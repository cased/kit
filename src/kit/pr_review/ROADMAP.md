# Kit Roadmap

This roadmap outlines planned features and improvements for kit, prioritized by user feedback and strategic value.

## 🚢 Recent ships

#### Per-User/Per-Organization Custom Context
Store custom guidelines, coding standards, and preferences that get automatically included in reviews.

```bash
# Example usage
kit profile create --name "company-standards" --file coding-guidelines.md
kit review --profile company-standards <pr-url>
```

Now in `0.7.0`.

## 📅 Planned Features

#### Feedback Learning System
Simple database to store review feedback and adapt over time.

```bash
# Example feedback workflow
kit review <pr-url>  # Generates review
kit feedback <review-id> --helpful/--not-helpful --notes "Missed performance issue"
kit insights  # Show what's working well
```

#### Inline Comments & GitHub Review API
Post comments directly on specific lines instead of single review comment.

```bash
kit review <pr-url> --mode inline  # Line-by-line comments
```

### 🎯 Medium Term

#### Multi-Model Consensus
Route different aspects to different models and aggregate insights.

```bash
kit review <pr-url> --consensus  # Use multiple models, combine results
```

#### Repository Context Learning
Learn which types of context are most valuable and adapt automatically.

#### IDE Integration
Real-time suggestions in VS Code and other editors while coding.

---

## 🔧 Technical Improvements

- **Model Router**: Intelligent routing to optimal models based on PR complexity
- **Context Optimization**: Smarter context selection to maximize LLM effectiveness
- **Plugin System**: Simple plugin architecture for custom analyzers

---

## 🎯 Success Metrics

### User Experience
- **Review Relevance**: >80% of suggestions rated as helpful
- **Response Time**: <30 seconds for standard reviews
- **Cost Efficiency**: <$0.10 per review for typical usage
- **Adoption Rate**: >90% of PRs reviewed within 1 hour

### Technical Quality
- **Uptime**: >99.9% availability for cloud service
- **Accuracy**: <5% false positive rate on issue detection
- **Performance**: Support for repositories up to 1M lines of code
- **Scalability**: Handle 10,000+ reviews per day per organization

### Business Impact
- **Code Quality**: Measurable improvement in code quality metrics
- **Development Velocity**: Faster PR review cycles
- **Bug Reduction**: Fewer bugs in production
- **Developer Satisfaction**: High satisfaction scores from development teams

---

## 📞 Get Involved

- **Feature Requests**: [Open an issue](https://github.com/cased/kit/issues) with your ideas
- **User Feedback**: Join our [Discord community](https://discord.gg/fbAVtCeU) soon for discussions
- **Contributions**: Submit PRs for features you'd like to see

---
