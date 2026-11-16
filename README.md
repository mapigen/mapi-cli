# Mapi CLI

**Universal API terminal toolchain, interactive spec manager, and discovery engine.**

`mapi-cli` provides an interactive terminal interface for managing, inspecting, and compiling OpenAPI specifications into optimized metadata catalogs consumed by the [`mapi`](https://github.com/mapigen/mapi) core SDK and LLM runtimes like Nodus / Mapidex.

---

## Installation

```bash
pip install mapi-cli
```

---

## Core Commands

### 1. Interactive Download TUI (`mapi download`)
Launch a full-screen Textual TUI to browse registered API providers, inspect local download status, and download specifications with real-time progress indicators:

```bash
# Launch interactive TUI
mapi download

# Non-interactive CLI downloads
mapi download pokeapi
mapi download --all
```
* **$\uparrow$/$\downarrow$ or `j`/`k`**: Navigate provider list.
* **`/`**: Live fuzzy search filter.
* **`Enter`**: Download and compile selected provider.
* **`a`**: Download all remote specifications.
* **`f`**: Toggle force overwrite mode.
* **`q`**: Quit.

### 2. Service & Provider Discovery (`mapi apis`)
```bash
# List all registered providers and local compile status
mapi apis

# Inspect operations for a specific provider
mapi apis discord

# Filter operations by HTTP method or search term
mapi apis discord -m post
mapi apis discord message
```

### 3. Operation Listing & Method Filtering (`mapi ops`)
```bash
# List operations with flexible positional or flagged filters
mapi ops discord REST
mapi ops discord post
mapi ops discord REST -m post,delete
mapi ops discord -m post message
```

### 4. Global Search (`mapi search`)
Fuzzy search across providers, APIs, operations, paths, summaries, and HTTP methods:

```bash
mapi search "create_message"
mapi search "pokemon" -m get
```

### 5. Operation Schema Inspection (`mapi describe`)
Inspect parameters, types, required flags, and example calls:

```bash
mapi describe pokeapi REST pokemon_retrieve
# or composite shorthand
mapi describe pokeapi/REST/pokemon_retrieve
```

### 6. Direct API Execution (`mapi call`)
Execute API calls directly from the terminal with automatic type coercion:

```bash
mapi call pokeapi REST pokemon_retrieve id=ditto
```

---

## Diagnostic & Maintainer Tools

* **`mapi doctor`**: Diagnostic checks on python environment, active data directory, and network connectivity.
* **`mapi path`**: Display or configure the active `platformdirs` storage path.
* **`mapi validate`**: Validate data directory schema integrity, JSON schema compatibility, and parameter `$ref` graphs.
* **`mapi compile`**: Maintainer tool to rebuild `mapi-registry.json` from disk metadata.

---

## License

Apache 2.0 License — see [LICENSE](../LICENSE) for details.
