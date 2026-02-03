# Development Standards

This project follows development standards to ensure consistency, maintainability, and quality.

## Base Standards

For foundational standards, refer to [ap-base standards](https://github.com/jewzaam/ap-base/tree/main/standards):

- **Project Structure**: `project-structure.md`
- **Naming Conventions**: `naming.md`
- **Testing**: `testing.md`
- **Makefile**: `makefile.md`
- **GitHub Workflows**: `github-workflows.md`
- **CLI Design**: `cli.md`
- **README Format**: `readme-format.md`
- **Logging & Progress**: `logging-progress.md`

## Project-Specific Standards

Standards specific to this project and similar service-oriented applications:

| Standard | Description |
|----------|-------------|
| [services.md](services.md) | API design, FastAPI patterns, async services |
| [authentication.md](authentication.md) | OAuth, sessions, token management |
| [persistent-storage.md](persistent-storage.md) | Database design, migrations, encryption |
| [user-interfaces.md](user-interfaces.md) | API responses, error handling, UX patterns |

## Deviations from ap-base

Notable modifications or extensions to ap-base standards:

1. **Python Version**: Minimum 3.11 (vs 3.10 in ap-base) due to async improvements
2. **Line Length**: 88 characters (matching Black, consistent with ap-base)
3. **Additional Linting**: Using both ruff and flake8 for comprehensive coverage

## Future Considerations

These standards are living documents. Areas to develop:

- [ ] Observability (metrics, tracing, health checks)
- [ ] Deployment patterns (containers, configuration)
- [ ] API versioning strategy
- [ ] Rate limiting and throttling
- [ ] Caching strategies
