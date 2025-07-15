# Kit Client Libraries

This directory contains client libraries for various programming languages that wrap the Kit CLI.

## Available Clients

- **TypeScript** (`typescript/`) - Node.js/TypeScript wrapper for Kit CLI
  - Status: In development
  - Install: `npm install @cased/kit` (once published)

## Planned Clients

- **Go** (`go/`) - Go client for Kit
- **Rust** (`rust/`) - Rust client for Kit
- **Ruby** (`ruby/`) - Ruby client for Kit

## Design Principles

All client libraries follow these principles:

1. **Shell out to CLI** - Clients wrap the Kit CLI rather than reimplementing functionality
2. **Type safety** - Provide strong typing for all commands and options
3. **Async/Promise-based** - Use language-appropriate async patterns
4. **Error handling** - Parse and wrap CLI errors into language-specific error types
5. **Zero Python dependencies** - Users only need Kit CLI installed, not Python packages

## Contributing

When adding a new client library:

1. Create a new directory under `clients/`
2. Include a README with installation and usage instructions
3. Follow the language's conventions and best practices
4. Provide comprehensive type definitions
5. Include tests that mock the CLI output
6. Add examples demonstrating common use cases 