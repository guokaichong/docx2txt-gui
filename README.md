# DocX 优雅阅读器

本地 `.docx` 文件解析与格式化导出工具，基于 **Tauri 2** 构建。

## 功能特性

- 拖拽添加 `.docx` 文件，无需安装 MS Word
- 智能分类预览：自我评价 / 基本信息 / 服务项目 / 地址 / 备注 / 服务价格
- 键盘翻页：↑↓ 切换文件
- 导出为 `.txt` 或 `.md` 格式
- 支持批量处理

## 构建

### 本地构建（需 Rust 环境）

```bash
# 1. 安装 Rust（已配置清华镜像）
rustup default stable

# 2. 安装 Tauri CLI
cargo install tauri-cli

# 3. 开发模式
npm install
cargo tauri dev

# 4. 生产构建
cargo tauri build
```

### 远程 CI 构建（推荐）

推送 tag 即可触发 GitHub Actions 自动构建：

```bash
git tag v1.0.0
git push origin v1.0.0
```

构建产物自动发布到 GitHub Releases，包含：
- Windows x64 `.msi` 安装包 + `.exe`
- macOS x64 `.dmg`
- macOS ARM64 `.dmg`

## 技术架构

| 层级 | 技术 |
|------|------|
| 框架 | Tauri 2.x |
| 前端 | Vanilla HTML/CSS/JS |
| 后端 | Rust（原生解析 docx = ZIP+XML） |
| CI | GitHub Actions |
| 产物 | 跨平台可执行文件 |

## 项目结构

```
docx2txt_gui/
├── index.html          # 前端 UI
├── package.json
├── SPEC.md             # 功能规格说明
├── README.md
├── .github/workflows/build.yml   # CI 构建流水线
└── src-tauri/
    ├── Cargo.toml
    ├── tauri.conf.json
    ├── capabilities/default.json
    ├── icons/icon.ico
    └── src/
        ├── lib.rs      # Rust 解析引擎
        └── main.rs     # 入口
```
