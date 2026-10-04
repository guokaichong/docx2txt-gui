use quick_xml::events::Event;
use quick_xml::Reader;
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use tauri::command;

const NS: &str = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";

#[derive(Serialize)]
pub struct DocxResult {
    pub paragraphs: Vec<String>,
    pub formatted: String,
}

// ── 解析引擎 ─────────────────────────────────────────────

fn parse_docx_raw(path: &str) -> Result<Vec<String>, String> {
    let path = Path::new(path);
    let file = fs::File::open(path).map_err(|e| format!("文件打开失败：{}", e))?;
    let mut zip = zip::ZipArchive::new(file).map_err(|e| format!("ZIP 解析失败：{}", e))?;

    let mut doc_xml = String::new();
    {
        let mut doc = zip
            .by_name("word/document.xml")
            .map_err(|_| "docx 内部结构异常：未找到 word/document.xml")?;
        doc.read_to_string(&mut doc_xml)
            .map_err(|e| format!("XML 读取失败：{}", e))?;
    }

    let mut reader = Reader::from_str(&doc_xml);
    reader.config_mut().trim_text(true);

    let mut paragraphs: Vec<String> = Vec::new();
    let mut current_para: Vec<String> = Vec::new();

    loop {
        match reader.read_event() {
            Ok(Event::Start(ref e)) if e.local_name().as_ref() == b"p" => {
                current_para.clear();
            }
            Ok(Event::Empty(ref e)) if e.local_name().as_ref() == b"br" => {
                current_para.push('\n'.to_string());
            }
            Ok(Event::Start(ref e)) if e.local_name().as_ref() == b"t" => {
                let mut buf = Vec::new();
                loop {
                    match reader.read_event_into(&mut buf) {
                        Ok(Event::Text(ref e)) => {
                            current_para.push(e.unescape().unwrap_or_default().to_string());
                        }
                        Ok(Event::CData(ref e)) => {
                            current_para.push(e.unescape().unwrap_or_default().to_string());
                        }
                        _ => break,
                    }
                    buf.clear();
                }
            }
            Ok(Event::Empty(ref e)) if e.local_name().as_ref() == b"br" => {
                current_para.push('\n'.to_string());
            }
            Ok(Event::End(ref e)) if e.local_name().as_ref() == b"p" => {
                let text = current_para.join("");
                let text = text.replace('\u{A0}', " ").trim().to_string();
                if !text.is_empty() {
                    for line in text.split('\n') {
                        let line = line.trim();
                        if !line.is_empty() {
                            paragraphs.push(line.to_string());
                        }
                    }
                }
            }
            Ok(Event::Eof) => break,
            _ => {}
        }
    }

    Ok(paragraphs)
}

// ── 格式化引擎 ────────────────────────────────────────────

fn format_content(paragraphs: &[String]) -> String {
    let div = "─".repeat(42);

    let service_re = Regex::new(
        "(十指弹琴|过水服务|胸滑|舌尖漫游|舌尖毒龙|共浴|浴室挑逗|水中萧|花式吹箫|69互动|激情爱爱|各类制服)((（[^）]*）)?)",
    )
    .unwrap();

    let price_re = Regex::new(r"^([PpP]+)\s*(\d[\d分钟次小时]*)").unwrap();
    let baoshi_re = Regex::new(r"^包时\s*(\d[\d分钟次小时]*)").unwrap();
    let addr_re = Regex::new(r"惠州市|地址").unwrap();
    let info_re = Regex::new(r"\d{2}年|身高\d|体重\d|胸围").unwrap();
    let ban_re = Regex::new(r"🈲").unwrap();

    let mut lines: Vec<String> = Vec::new();
    let mut price_buf: Vec<String> = Vec::new();

    for p in paragraphs {
        let p = p.trim().replace('\u{A0}', " ");
        if p.is_empty() {
            continue;
        }

        // 价格行
        if p.contains("P") || p.contains("p") || p.contains("包时") {
            price_buf.push(p.clone());
            continue;
        }

        // 地址
        if addr_re.is_match(&p) {
            let addr = p.replace("地址", "").trim().to_string();
            lines.extend([
                "".to_string(),
                div.clone(),
                format!("　地址"),
                div.clone(),
                format!("　　{}", addr),
            ]);
            continue;
        }

        // 备注
        if ban_re.is_match(&p) {
            let bans: Vec<String> = ban_re
                .captures_iter(&p)
                .map(|c| {
                    let start = c.get(0).unwrap().end();
                    let rest = &p[start..];
                    let m = regex::Regex::new(r"^[^🈲\s]{1,4}")
                        .unwrap()
                        .find(&rest)
                        .map(|m| m.as_str().to_string())
                        .unwrap_or_default();
                    m
                })
                .filter(|s| !s.is_empty())
                .collect();
            lines.extend([
                "".to_string(),
                div.clone(),
                format!("　备注"),
                div.clone(),
                format!("　　禁止：{}", bans.join("　")),
            ]);
            continue;
        }

        // 自我评价
        if p.starts_with("自我评价") {
            let body = p.replace("自我评价", "").trim().to_string();
            lines.extend([
                "".to_string(),
                div.clone(),
                format!("　自我评价"),
                div.clone(),
                format!("　　{}", body),
            ]);
            continue;
        }

        // 基本信息
        if info_re.is_match(&p) {
            let parts: Vec<String> = p
                .split(|c| c == '，' || c == ',' || c == '、' || c == ' ')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();
            lines.extend(
                std::iter::empty::<String>()
                    .chain(std::iter::once("".to_string()))
                    .chain(std::iter::once(div.clone()))
                    .chain(std::iter::once(format!("　基本信息")))
                    .chain(std::iter::once(div.clone()))
                    .chain(parts.iter().map(|s| format!("　◆ {}", s))),
            );
            continue;
        }

        // 服务项目
        if service_re.is_match(&p) {
            let text = p.replace("服务：", "").replace("服务", "").trim().to_string();
            let mut items: Vec<String> = Vec::new();
            let mut last_end = 0;

            for cap in service_re.captures_iter(&text) {
                let m = cap.get(0).unwrap();
                if m.start() > last_end {
                    // skip prefix
                }
                let item = format!(
                    "{}{}",
                    cap.get(1).unwrap().as_str(),
                    cap.get(2).map(|m| m.as_str()).unwrap_or("")
                );
                items.push(item);
                last_end = m.end();
            }

            if last_end < text.len() {
                let tail = text[last_end..].trim().to_string();
                if !tail.is_empty() {
                    if let Some(last) = items.last_mut() {
                        *last += &tail;
                    } else {
                        items.push(tail);
                    }
                }
            }

            lines.extend(
                std::iter::empty::<String>()
                    .chain(std::iter::once("".to_string()))
                    .chain(std::iter::once(div.clone()))
                    .chain(std::iter::once(format!("　服务项目")))
                    .chain(std::iter::once(div.clone()))
                    .chain(items.iter().map(|s| format!("　◆ {}", s))),
            );
            continue;
        }

        lines.push(p);
    }

    // 价格节
    if !price_buf.is_empty() {
        lines.extend([
            "".to_string(),
            div.clone(),
            format!("　服务价格"),
            div.clone(),
        ]);
        for pv in &price_buf {
            let pv = pv.trim().replace('\u{A0}', " ");
            let pv = pv.replace("价格", "").trim().to_string();

            if let Some(caps) = price_re.captures(&pv) {
                let prefix = caps.get(1).unwrap().as_str();
                let val = caps.get(2).unwrap().as_str();
                let tag = if prefix.eq_ignore_ascii_case("PP") {
                    "双人套餐"
                } else {
                    "单次体验"
                };
                lines.push(format!("　{}　　{}{}", tag, prefix, val));
            } else if let Some(caps) = baoshi_re.captures(&pv) {
                lines.push(format!(
                    "　包时套餐　包时{}",
                    caps.get(1).unwrap().as_str()
                ));
            } else {
                lines.push(format!("　{}", pv));
            }
        }
    }

    lines.extend(["".to_string(), div.clone()]);
    lines.join("\n")
}

fn to_markdown(paragraphs: &[String]) -> String {
    let mut lines: Vec<String> = vec!["# 文档内容".to_string()];

    let service_re = Regex::new(
        "(十指弹琴|过水服务|胸滑|舌尖漫游|舌尖毒龙|共浴|浴室挑逗|水中萧|花式吹箫|69互动|激情爱爱|各类制服)((（[^）]*）)?)",
    )
    .unwrap();
    let price_re = Regex::new(r"^([PpP]+)\s*(\d[\d分钟次小时]*)").unwrap();
    let baoshi_re = Regex::new(r"^包时\s*(\d[\d分钟次小时]*)").unwrap();

    let mut price_buf: Vec<String> = Vec::new();

    for p in paragraphs {
        let p = p.trim().replace('\u{A0}', " ");
        if p.is_empty() {
            continue;
        }

        if p.contains("P") || p.contains("p") || p.contains("包时") {
            price_buf.push(p.clone());
            continue;
        }

        if p.contains("惠州市") || p.contains("地址") {
            let addr = p.replace("地址", "").replace("惠州市", "惠州市").trim().to_string();
            lines.extend(["\n## 地址".to_string(), format!("\n{}\n", addr)]);
            continue;
        }

        if p.contains("🈲") {
            let bans: Vec<String> = regex::Regex::new(r"🈲([^🈲\s]{1,4})")
                .unwrap()
                .captures_iter(&p)
                .map(|c| c.get(1).unwrap().as_str().to_string())
                .collect();
            lines.extend([
                "\n## 备注".to_string(),
                format!("\n**禁止：** {}\n", bans.join(" / ")),
            ]);
            continue;
        }

        if p.starts_with("自我评价") {
            let body = p.replace("自我评价", "").trim().to_string();
            lines.extend(["\n## 自我评价".to_string(), format!("\n{}\n", body)]);
            continue;
        }

        if regex::Regex::new(r"\d{2}年|身高\d|体重\d|胸围")
            .unwrap()
            .is_match(&p)
        {
            let parts: Vec<String> = p
                .split(|c| c == '，' || c == ',' || c == '、' || c == ' ')
                .map(|s| s.trim().to_string())
                .filter(|s| !s.is_empty())
                .collect();
            lines.push("\n## 基本信息\n".to_string());
            for s in &parts {
                lines.push(format!("- {}", s));
            }
            lines.push("\n".to_string());
            continue;
        }

        if service_re.is_match(&p) {
            let text = p.replace("服务：", "").replace("服务", "").trim().to_string();
            let mut items: Vec<String> = Vec::new();
            for cap in service_re.captures_iter(&text) {
                let item = format!(
                    "{}{}",
                    cap.get(1).unwrap().as_str(),
                    cap.get(2).map(|m| m.as_str()).unwrap_or("")
                );
                items.push(item);
            }
            lines.push("\n## 服务项目\n".to_string());
            for s in &items {
                lines.push(format!("- {}", s));
            }
            lines.push("\n".to_string());
            continue;
        }
    }

    if !price_buf.is_empty() {
        lines.push("\n## 服务价格\n".to_string());
        for pv in &price_buf {
            let pv = pv.trim().replace('\u{A0}', " ").replace("价格", "").trim().to_string();
            if let Some(caps) = price_re.captures(&pv) {
                let tag = if caps.get(1).unwrap().as_str().eq_ignore_ascii_case("PP") {
                    "双人套餐"
                } else {
                    "单次体验"
                };
                lines.push(format!(
                    "- **{}**：{}{}",
                    tag,
                    caps.get(1).unwrap().as_str(),
                    caps.get(2).unwrap().as_str()
                ));
            } else if let Some(caps) = baoshi_re.captures(&pv) {
                lines.push(format!("- **包时套餐**：{}", caps.get(1).unwrap().as_str()));
            }
        }
    }

    lines.join("\n")
}

// ── Tauri 命令 ────────────────────────────────────────────

#[command]
pub fn parse_docx(path: String) -> Result<DocxResult, String> {
    log::info!("parse_docx: {}", path);
    let paragraphs = parse_docx_raw(&path)?;
    let formatted = format_content(&paragraphs);
    Ok(DocxResult {
        paragraphs,
        formatted,
    })
}

#[command]
pub fn export_txt(file_path: String, out_path: String) -> Result<(), String> {
    log::info!("export_txt: {} -> {}", file_path, out_path);
    let paragraphs = parse_docx_raw(&file_path)?;
    let content = format_content(&paragraphs);
    fs::write(&out_path, content).map_err(|e| format!("写入失败：{}", e))?;
    Ok(())
}

#[command]
pub fn export_md(file_path: String, out_path: String) -> Result<(), String> {
    log::info!("export_md: {} -> {}", file_path, out_path);
    let paragraphs = parse_docx_raw(&file_path)?;
    let content = to_markdown(&paragraphs);
    fs::write(&out_path, content).map_err(|e| format!("写入失败：{}", e))?;
    Ok(())
}
