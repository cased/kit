# Kit AI-Powered PR Reviewer

`kit` includes a production-ready CLI-based pull request reviewer that provides intelligent, comprehensive code reviews using Anthropic or OpenAI models, with cost transparency and professional-grade analysis.

## 🚀 Quick Start

```bash
# 1. Install kit
pip install cased-kit

# 2. Initialize configuration
kit review --init-config

# 3. Set your API keys
export KIT_GITHUB_TOKEN="ghp_your_github_token"
export KIT_ANTHROPIC_TOKEN="sk-ant-your_anthropic_key"

# 4. Review any GitHub PR
kit review https://github.com/owner/repo/pull/123

# 5. Test without posting (dry run)
kit review --dry-run https://github.com/owner/repo/pull/123
```

## 💰 Cost Economics

Kit provides **exceptional value** with transparent pricing. Based on real-world testing:

### **Dynamic Pricing via Helicone API**

Kit now fetches real-time pricing data from [Helicone's API](https://www.helicone.ai/llm-cost), ensuring:
- **Always Current**: No more outdated pricing - automatically updates hourly
- **300+ Models**: Access pricing for models across all major providers
- **Zero Configuration**: Works out of the box with no setup required
- **Graceful Fallback**: Uses minimal defaults if API is unavailable

### **Actual Cost Data (Typical 3-6 file PR)**

| Mode | Typical Cost Range | Speed | Use Case |
|------|------------|-------|----------|
| **Standard** | $0.05-0.20 | 15-45 sec | Daily development - **recommended** |
| **Agentic** | $0.36-2.57 | 1-5 min | Research/experimentation |

### **Real-World Monthly Costs**

**Key benefits**:
- No per-seat licensing - costs scale with usage, not team size
- Whole repo context and multiple code tools - all powered by kit
- Complete cost transparency - see exact LLM costs with no markup

### **Complete Pricing Matrix (Real Test Results)**

Tested on a large 12-file PR with comprehensive analysis. Costs are often lower (e.g., sonnet4 on most PRs we get
at 8 cents a review).

| Model | Provider | Cost | Input Tokens | Output Tokens | $/Million Input | $/Million Output | Speed Tier |
|-------|----------|------|--------------|---------------|-----------------|------------------|------------|
| **gpt-4.1-nano** | OpenAI | **$0.0046** | 42,002 | 885 | $0.10 | $0.40 | ⚡ Ultra Budget |
| **gpt-4o-mini** | OpenAI | **$0.0067** | 40,839 | 902 | $0.15 | $0.60 | ⚡ Budget |
| **gemini-2.5-flash** | Google | **$0.0069** | 42,000 | 1,000 | $0.15 | $0.60 | ⚡ Budget |
| **gemini-1.5-flash-8b** | Google | **$0.0032** | 42,000 | 1,000 | $0.075 | $0.30 | ⚡ Ultra Budget |
| **gpt-4.1-mini** | OpenAI | **$0.0191** | 42,026 | 1,460 | $0.40 | $1.60 | ⚡ Budget |
| **claude-3-5-haiku-20241022** | Anthropic | **$0.0447** | 52,627 | 660 | $0.80 | $4.00 | ⚡ Budget |
| **gpt-4.1** | OpenAI | **$0.1010** | 42,007 | 2,122 | $2.00 | $8.00 | 🚀 Good Value |
| **gpt-4o** | OpenAI | **$0.1089** | 40,873 | 672 | $2.50 | $10.00 | 🚀 Good Value |
| **gemini-1.5-flash** | Google | **$0.0069** | 42,000 | 1,000 | $0.15 | $0.60 | 🚀 Good Value |
| **gemini-1.5-pro** | Google | **$0.1150** | 42,000 | 1,000 | $2.50 | $10.00 | 🚀 Good Value |
| **claude-sonnet-4-20250514** | Anthropic | **$0.1759** | 52,667 | 1,195 | $3.00 | $15.00 | 🚀 **Recommended** |
| **claude-3-5-sonnet-20241022** | Anthropic | **$0.1774** | 52,593 | 1,307 | $3.00 | $15.00 | 🚀 Fast |
| **gemini-2.5-pro** | Google | **$0.1150** | 42,000 | 1,000 | $2.50 | $15.00 | 🚀 Advanced |
| **gpt-4-turbo** | OpenAI | **$0.4258** | 40,598 | 659 | $10.00 | $30.00 | 💰 Premium |
| **claude-opus-4-20250514** | Anthropic | **$0.9086** | 52,597 | 1,595 | $15.00 | $75.00 | 🧠 Most Capable |

**Key Insights:**
- **284x price difference** between cheapest (Gemini 1.5 Flash 8B) and most capable (Claude Opus 4)
- **Gemini 1.5 Flash 8B** offers exceptional value at $0.003 per large PR - new ultra-budget champion
- **Google Gemini models** provide excellent price-performance across all tiers
- **GPT-4.1-nano** remains ultra-budget option at $0.005 per large PR
- **Claude Sonnet 4** (default) balances cost and quality - comprehensive repository analysis
- **OpenAI models** use fewer input tokens (~40k vs ~52k) but deliver comparable analysis depth
- **GPT-4.1 series** provides excellent mid-range options between ultra-budget and premium

> **💡 Pro Tip:** Don't underestimate the smaller models! GPT-4.1-nano and GPT-4o-mini deliver surprisingly useful reviews. For most small teams (20-50 PRs/month), you can get comprehensive AI code reviews for **less than $1/month** with these budget models. That's potentially transformative value for the cost of a coffee.

**Projected Monthly Costs (Based on Real Data):**

| Team Size | Gemini 1.5 Flash 8B (Ultra Budget) | GPT-4.1-nano (Ultra Budget) | Claude Sonnet 4 (Recommended) | Claude Opus 4 (Premium) |
|-----------|--------------------------------------|------------------------------|--------------------------------|--------------------------|
| **Small** (20 PRs/month) | $0.06 | $0.09 | $3.52 | $18.17 |
| **Medium** (100 PRs/month) | $0.32 | $0.46 | $17.59 | $90.86 |
| **Larger** (500 PRs/month) | $1.60 | $2.30 | $87.95 | $454.30 |

*Assumes mix of PR sizes with large PRs (12+ files) representing ~30% of reviews*

## 🎯 Review Modes Deep Dive

### Standard Mode (Recommended)

**How it works**: Leverages kit's repository intelligence for comprehensive reviews with symbol analysis and cross-codebase impact assessment.

**Strengths**:
- Excellent quality-to-cost ratio
- Repository context and symbol analysis
- Identifies impact on functions/classes used elsewhere
- Fast single-pass execution
- Professional, actionable feedback

**Example capabilities**:
- Identifies that a function is used in 23 other places
- Suggests specific code improvements with examples
- Analyzes dependency changes and their implications
- Provides architectural guidance based on repository structure

### Agentic Mode (Experimental)

**How it works**: Uses multi-turn analysis where the AI investigates the PR using kit's tools through iterative exploration. Expensive, and with unclear quality improvenents.

**Important Notes**:
- **Experimental feature** - currently serves as research artifact
- Can produce overconfident conclusions about non-existent issues
- Significantly more expensive than other modes
- Demonstrates that complex approaches don't always yield better results

**Best for**: Research, experimentation, understanding current AI agent limitations

## 🎯 Priority Filtering

Kit organizes review findings into three priority levels and allows you to filter results to focus on what matters most:

### Priority Levels

- **High Priority**: Critical security vulnerabilities, breaking changes, data loss risks
- **Medium Priority**: Performance issues, logic errors, architectural concerns  
- **Low Priority**: Code style, minor optimizations, documentation improvements

### Usage

**CLI Options:**
```bash
# Show only critical issues
kit review --priority=high <pr-url>

# Show critical and important issues
kit review --priority=high,medium <pr-url>

# Show only style/documentation issues
kit review --priority=low <pr-url>

# Default: show all priorities
kit review <pr-url>
```

**Configuration File:**
```yaml
review:
  priority_filter: ["high", "medium"]  # Only show high and medium priority
```

### Benefits

- **Focus Time**: Quickly identify critical issues that need immediate attention
- **Staged Reviews**: Handle high priority issues first, low priority in follow-up
- **CI/CD Integration**: Use `--priority=high` in CI to only block on critical issues
- **Learning**: Use `--priority=low` to learn about code style improvements
- **Cost Optimization**: High priority reviews are shorter and cost less

### Output Example

```bash
$ kit review --priority=high https://github.com/example/repo/pull/42
```

## 🎯 Key Features

### Intelligent Analysis
- Deep code understanding using repository cloning and analysis
- Context-aware reviews with full codebase knowledge
- Multi-language support for any language kit supports
- Security and architecture analysis

### Professional Output
- Concise, actionable feedback without unnecessary verbosity
- Priority-based issue ranking (High/Medium/Low)
- Clickable GitHub links for all file references
- Professional tone without dramatic language

### Cost Transparency
- Real-time cost tracking showing exact LLM usage
- Token breakdown (input/output) for understanding cost drivers
- Model information showing which LLM provided the analysis

### Priority Filtering
- Filter review output by priority level (High/Medium/Low)
- Focus on critical issues with `--priority=high`
- Combine priorities: `--priority=high,medium`
- Configurable in config file or via CLI flag
- Transparent filtering with issue count summary

### Enterprise Features
- Repository caching for faster repeat reviews
- Multiple LLM support (Anthropic Claude, OpenAI GPT-4)
- Configurable analysis depth and turn limits
- GitHub integration with token-based authentication

## 📋 Custom Context Profiles

Kit supports organization-specific coding standards and review guidelines through **custom context profiles**. These profiles automatically inject your company's coding standards, security requirements, and style guidelines into every PR review, ensuring consistent and organization-aligned feedback.

### Why Use Profiles?

- **Consistency**: All reviews follow your organization's standards automatically
- **Efficiency**: No need to manually specify guidelines for each review
- **Customization**: Different teams can have different standards (backend vs frontend, security vs performance focus)
- **Knowledge Sharing**: Encode institutional knowledge into reusable profiles
- **Compliance**: Ensure security and regulatory requirements are consistently checked

### Quick Start

```bash
# Create a profile from a file containing your coding standards
kit review-profile create --name company-standards --file coding-guidelines.md --description "Acme Corp coding standards"

# Use the profile in reviews
kit review --profile company-standards https://github.com/owner/repo/pull/123

# List all available profiles
kit review-profile list
```

### Profile Management

#### Creating Profiles

**From a file (recommended):**
```bash
kit review-profile create \
  --name python-security \
  --file security-guidelines.md \
  --description "Python security best practices" \
  --tags "security,python"
```

**Interactive creation:**
```bash
kit review-profile create \
  --name company-standards \
  --description "Company coding standards"
# Then type your guidelines, press Enter for a new line, then Ctrl+D to finish
```

#### Managing Profiles

```bash
# List all profiles
kit review-profile list

# Show profile details
kit review-profile show --name company-standards

# Edit a profile
kit review-profile edit --name company-standards --file updated-guidelines.md

# Copy a profile
kit review-profile copy --name company-standards --target team-standards

# Export for sharing
kit review-profile export --name company-standards --file exported-standards.md

# Import shared profile
kit review-profile import --file shared-guidelines.md --name imported-standards

# Delete a profile
kit review-profile delete --name old-profile
```

### Example Profile Content

Here's an example of effective profile content:

```markdown
**Company Code Review Standards:**

1. **Security Requirements:**
   - All user input must be validated and sanitized
   - No hardcoded credentials or secrets
   - Use parameterized queries for database operations
   - Implement proper authentication and authorization

2. **Performance Guidelines:**
   - Avoid N+1 queries in database operations
   - Use appropriate data structures (prefer sets for membership tests)
   - Consider memory usage for large data processing
   - Use async/await for I/O bound operations

3. **Code Quality Standards:**
   - All functions must have docstrings
   - Use type hints for function parameters and return values
   - Follow DRY principle - no duplicate code blocks
   - Maximum function length: 50 lines

4. **Testing Requirements:**
   - All new features must include unit tests
   - Minimum 80% test coverage for new code
   - Integration tests for API endpoints
   - Mock external dependencies in tests

5. **Documentation Standards:**
   - README files must be updated for new features
   - API changes require documentation updates
   - Include examples in docstrings

6. **Python-Specific Rules:**
   - Use f-strings for string formatting
   - Prefer list/dict comprehensions when readable
   - Use pathlib instead of os.path
   - Follow PEP 8 formatting standards
```

### Using Profiles in Reviews

**CLI Usage:**
```bash
# Standard review with custom context
kit review --profile company-standards https://github.com/owner/repo/pull/123

# Agentic review with custom context
kit review --profile company-standards --agentic https://github.com/owner/repo/pull/123

# Combine with other options
kit review --profile security-focused --priority=high --dry-run https://github.com/owner/repo/pull/123
```

**CI/CD Integration:**
```yaml
- name: AI Review with Company Standards
  run: |
    kit review --profile company-standards ${{ github.event.pull_request.html_url }}
  env:
    KIT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    KIT_ANTHROPIC_TOKEN: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Profile Organization

#### Team-Specific Profiles

```bash
# Backend team profile
kit review-profile create --name backend-api \
  --description "Backend API development standards" \
  --tags "backend,api,python"

# Frontend team profile  
kit review-profile create --name frontend-react \
  --description "React frontend development standards" \
  --tags "frontend,react,typescript"

# Security team profile
kit review-profile create --name security-hardening \
  --description "Security-focused review guidelines" \
  --tags "security,compliance"
```

#### Project-Specific Profiles

```bash
# Different standards for different project types
kit review-profile create --name microservice-standards --description "Microservice architecture guidelines"
kit review-profile create --name data-pipeline-standards --description "Data pipeline best practices"
kit review-profile create --name mobile-app-standards --description "Mobile app development standards"
```

### Best Practices

#### Writing Effective Profiles

1. **Be Specific**: Include concrete examples and specific requirements
2. **Focus on Intent**: Explain *why* certain practices are required
3. **Use Examples**: Show good and bad code examples when possible
4. **Stay Current**: Regular update profiles as standards evolve
5. **Tag Appropriately**: Use tags for easy organization and discovery

#### Profile Management Workflow

1. **Start Small**: Begin with essential standards, expand over time
2. **Team Input**: Involve team members in creating and updating profiles
3. **Version Control**: Export profiles and version them alongside your code
4. **Regular Reviews**: Periodically review and update profile content
5. **Share Across Teams**: Use export/import to share successful profiles

#### Example: Security-Focused Profile

```markdown
**Security Review Checklist:**

- **Input Validation**: All user inputs must be validated against expected formats
- **SQL Injection Prevention**: Use parameterized queries, never string concatenation
- **XSS Prevention**: Sanitize all user content before rendering
- **Authentication**: Verify all endpoints require proper authentication
- **Authorization**: Check that users can only access resources they own
- **Secrets Management**: No hardcoded API keys, tokens, or passwords
- **Logging**: Sensitive data must not appear in logs
- **Error Handling**: Don't expose stack traces or system information
- **Dependencies**: Check for known vulnerabilities in dependencies
- **HTTPS**: All external communications must use HTTPS
```

### Storage and Sharing

- **Location**: Profiles are stored in `~/.kit/profiles/` as YAML files
- **Format**: Human-readable YAML with metadata and content
- **Sharing**: Export/import functionality for team collaboration
- **Backup**: Include profiles in your team's configuration management

### Integration with Review Process

When a profile is specified, the custom context is automatically injected into the review prompt as **"Custom Review Guidelines"**, ensuring the AI reviewer follows your organization's specific standards while maintaining all other kit functionality like repository analysis and symbol extraction.

## 📋 Setup Instructions

### 1. GitHub Token Setup

You need a GitHub token with appropriate permissions:

#### Classic Personal Access Token (Recommended)

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**
2. Click **"Generate new token (classic)"**
3. Select scopes:
   - **Public repos**: `public_repo`
   - **Private repos**: `repo` (includes public access)
4. Copy token format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 2. LLM API Keys

#### Anthropic Claude (Recommended)
1. Get API key from https://console.anthropic.com/
2. Format: `sk-ant-xxxxxxxxxxxxxxxxx`
3. Set: `export KIT_ANTHROPIC_TOKEN="your_key"`

#### OpenAI GPT-4
1. Get API key from https://platform.openai.com/
2. Format: `sk-xxxxxxxxxxxxxxxxx`
3. Set: `export KIT_OPENAI_TOKEN="your_key"`

#### Custom OpenAI Compatible Providers

Kit supports any OpenAI compatible API provider by setting a custom `api_base_url`. Popular options include:

**Together AI** (Cost-effective, fast inference)
```bash
export KIT_OPENAI_TOKEN="your_together_api_key"
```

**OpenRouter** (Access to many models via one API)
```bash  
export KIT_OPENAI_TOKEN="your_openrouter_api_key"
```

**Groq** (Ultra-fast inference)
```bash
export KIT_OPENAI_TOKEN="your_groq_api_key"
```

**Local OpenAI API Server** (e.g., text-generation-webui, vLLM)
```bash
export KIT_OPENAI_TOKEN="not-used"  # Local servers often don't need API keys
```

### 3. Configuration

#### Quick Setup
```bash
kit review --init-config
```

This creates `~/.kit/review-config.yaml` with defaults.

#### Manual Configuration

Edit `~/.kit/review-config.yaml`:

```yaml
github:
  token: ghp_your_token_here
  base_url: https://api.github.com

llm:
  provider: anthropic  # or "openai"
  model: claude-sonnet-4-20250514  # or "gpt-4o"
  api_key: sk-ant-your_key_here
  max_tokens: 4000
  temperature: 0.1

review:
  max_files: 50
  post_as_comment: true
  clone_for_analysis: true
  cache_repos: true
  agentic_max_turns: 15
  agentic_finalize_threshold: 10

# Optional: Custom LLM pricing
custom_pricing:
  anthropic:
    claude-sonnet-4-20250514:
      input_per_million: 3.00
      output_per_million: 15.00
  openai:
    gpt-4o:
      input_per_million: 2.50  
      output_per_million: 10.00
```

#### Custom OpenAI Compatible Provider Examples

**Together AI Configuration:**
```yaml
llm:
  provider: openai
  model: "meta-llama/Llama-3.3-70B-Instruct-Turbo"
  api_key: "your_together_api_key"
  api_base_url: "https://api.together.xyz/v1"
  max_tokens: 4000
  temperature: 0.1
```

**OpenRouter Configuration:**
```yaml
llm:
  provider: openai
  model: "anthropic/claude-3.5-sonnet"
  api_key: "your_openrouter_api_key" 
  api_base_url: "https://openrouter.ai/api/v1"
  max_tokens: 4000
  temperature: 0.1
```

**Groq Configuration:**
```yaml
llm:
  provider: openai
  model: "llama-3.3-70b-versatile"
  api_key: "your_groq_api_key"
  api_base_url: "https://api.groq.com/openai/v1"
  max_tokens: 4000
  temperature: 0.1
```

**Local OpenAI API Server Configuration:**
```yaml
llm:
  provider: openai
  model: "local-model-name"
  api_key: "not-used"  # Local servers often don't require API keys
  api_base_url: "http://localhost:8000/v1"
  max_tokens: 4000
  temperature: 0.1
```

## 🔧 Usage Examples

### Basic Review
```bash
# Standard mode (recommended)
kit review https://github.com/owner/repo/pull/123

# Dry run (formatted preview without posting)
kit review --dry-run https://github.com/owner/repo/pull/123

# Plain output for piping to other tools
kit review --plain https://github.com/owner/repo/pull/123
kit review -p https://github.com/owner/repo/pull/123

# Custom context profiles - apply organization standards
kit review --profile company-standards https://github.com/owner/repo/pull/123
kit review --profile python-security --priority=high https://github.com/owner/repo/pull/123

# Priority filtering - only show high priority issues
kit review --priority=high https://github.com/owner/repo/pull/123

# Priority filtering - show high and medium priority issues
kit review --priority=high,medium https://github.com/owner/repo/pull/123

# Priority filtering - only show low priority issues (code style, minor improvements)
kit review --priority=low https://github.com/owner/repo/pull/123

# Override model for specific review
kit review --model gpt-4.1-nano https://github.com/owner/repo/pull/123

# Combine all options
kit review --profile backend-api --priority=high --model gpt-4.1-nano --dry-run https://github.com/owner/repo/pull/123

# Pipe to Claude Code for implementation
kit review -p https://github.com/owner/repo/pull/123 | \
  claude "Implement all the suggestions from this code review"

# Agentic mode (experimental) with custom context
kit review --profile company-standards --agentic --agentic-turns 8 https://github.com/owner/repo/pull/123
```

### Profile Management
```bash
# Create profiles for different teams and projects
kit review-profile create --name company-standards --file coding-guidelines.md --description "Company coding standards"
kit review-profile create --name security-focused --description "Security review guidelines" --tags "security"

# List and manage profiles
kit review-profile list
kit review-profile show --name company-standards
kit review-profile edit --name company-standards --file updated-guidelines.md
kit review-profile delete --name old-profile
```

### Cache Management
```bash
# Check cache status
kit review-cache status

# Clean up old cached repos
kit review-cache cleanup

# Clear all cache
kit review-cache clear
```

## 🚀 CI/CD Integration

### GitHub Actions Setup

Add automated PR reviews to your repository with GitHub Actions. Kit integrates seamlessly into CI/CD pipelines for consistent, automated code review.

#### Basic Workflow

Create `.github/workflows/pr-review.yml`:

```yaml
name: AI PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    
    steps:
      - name: AI Code Review
        run: |
          pip install cased-kit
          kit review ${{ github.event.pull_request.html_url }}
        env:
          KIT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          KIT_ANTHROPIC_TOKEN: ${{ secrets.ANTHROPIC_API_KEY }}
```

#### Advanced Workflow with Error Handling

```yaml
name: Advanced AI PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    
    steps:
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          
      - name: Install Kit
        run: |
          pip install --upgrade pip
          pip install cased-kit
          
      - name: Dry Run Review (for testing)
        if: github.event.pull_request.draft
        run: |
          echo "🔍 Draft PR - running dry run only"
          kit review --dry-run ${{ github.event.pull_request.html_url }}
        env:
          KIT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          KIT_ANTHROPIC_TOKEN: ${{ secrets.ANTHROPIC_API_KEY }}
          
      - name: Full AI Review
        if: "!github.event.pull_request.draft"
        run: |
          echo "🤖 Running AI review for ready PR"
          kit review ${{ github.event.pull_request.html_url }}
        env:
          KIT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          KIT_ANTHROPIC_TOKEN: ${{ secrets.ANTHROPIC_API_KEY }}
          
      - name: Review Failed
        if: failure()
        run: |
          echo "❌ AI review failed - check logs for details"
          echo "This might be due to:"
          echo "- Missing API tokens"
          echo "- Rate limiting"
          echo "- Large PR size"
```

#### Budget-Conscious Workflow

```yaml
name: Budget AI PR Review
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read
    
    steps:
      - name: Budget AI Review (GPT-4.1-nano)
        run: |
          pip install cased-kit
          
          # Create budget config
          cat > ~/.kit/review-config.yaml << EOF
          github:
            token: env_github_token
          llm:
            provider: openai
            model: gpt-4.1-nano  # Ultra budget: ~$0.005 per PR
            api_key: env_openai_token
          review:
            post_as_comment: true
          EOF
          
          kit review ${{ github.event.pull_request.html_url }}
        env:
          KIT_GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          KIT_OPENAI_TOKEN: ${{ secrets.OPENAI_API_KEY }}
```

### Token Setup for CI/CD

#### Required Secrets

Add these secrets to your repository settings (`Settings` → `Secrets and variables` → `Actions`):

| Secret Name | Description | Required |
|-------------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic Claude API key (`sk-ant-...`) | For Claude models |
| `OPENAI_API_KEY` | OpenAI API key (`sk-...`) | For GPT models |

#### GitHub Token

- **GitHub token** is automatically available as `${{ secrets.GITHUB_TOKEN }}`
- Has write permissions to pull requests when `permissions` block is set
- No additional setup required

#### Security Best Practices

```yaml
# ✅ Good: Use organization/repository secrets
env:
  KIT_ANTHROPIC_TOKEN: ${{ secrets.ORG_ANTHROPIC_API_KEY }}
  
# Inherit from organization config file
- name: Download Org Config
  run: |
    curl -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \
         -o ~/.kit/review-config.yaml \
         https://raw.githubusercontent.com/your-org/kit-config/main/review-config.yaml
```

#### Audit and Compliance

```yaml
- name: Review Audit Log
  run: |
    echo "📊 Review completed for PR #${{ github.event.pull_request.number }}"
    echo "- Repository: ${{ github.repository }}"
    echo "- Author: ${{ github.event.pull_request.user.login }}"
    echo "- Timestamp: $(date -u)"
    echo "- Model: claude-sonnet-4-20250514"
    
    # Send to your audit system
    # curl -X POST your-audit-endpoint ...
```

## 🎯 Accuracy Validation

Kit provides several approaches to validate review accuracy:

### Built-in Quality Metrics

Every review includes objective quality scoring:

- **Reference Validation**: Checks if review references actual changed files
- **Line Number Validation**: Verifies line references are plausible
- **Specificity Analysis**: Counts concrete vs vague feedback
- **GitHub Link Validation**: Ensures links point to changed files
- **Content Relevance**: Measures alignment with actual code changes
- **Change Coverage**: Assesses coverage of major modifications

Example output:
```
📊 Review Quality Score: 0.75/1.0
📈 Metrics: {'file_references': 3, 'specific_issues': 5, 'github_links': 4}
```

### Validation Strategies

1. **Comparative Analysis**
   ```bash
   # Compare different modes on same PR
   kit review --dry-run <pr-url>
   kit review --dry-run --agentic <pr-url>
   ```

2. **Historical Tracking**
   - Track quality scores over time
   - Monitor for degradation patterns
   - Compare across different PR types

3. **Spot Checking**
   - Manually validate 10-20% of reviews
   - Focus on high-impact or low-scoring reviews
   - Document common failure patterns

4. **Cross-Validation**
   - Test same PR with different models
   - Compare Claude vs GPT-4 outputs
   - Use multiple team members for validation

Kit includes tools for systematic accuracy validation:

#### Cross-Mode Testing
```bash
# Test a PR across all modes and compare
python -m kit.pr_review.test_accuracy test --pr-url https://github.com/owner/repo/pull/123
```

#### Review Validation
```bash
# Validate an existing review
echo "## Summary\nThis PR adds..." > review.txt
python -m kit.pr_review.test_accuracy validate --pr-url <pr-url> --review-file review.txt
```

#### Regression Testing
```bash
# Test multiple PRs systematically
echo "https://github.com/owner/repo/pull/123" > pr_list.txt
echo "https://github.com/owner/repo/pull/124" >> pr_list.txt
python -m kit.pr_review.test_accuracy regression --pr-list pr_list.txt
```

Output example:
```
🧪 Testing PR: https://github.com/owner/repo/pull/123
🛠️ STANDARD MODE: $0.15 | 2,856 chars  
🤖 AGENTIC MODE: $1.25 | 4,102 chars

📊 Quality Scores: Standard: 0.84 | Agentic: 0.71*
*Agentic may produce false positives - use with caution
```

## Environment Variables

| Purpose | Variable |
|---------|----------|
| GitHub Token | `KIT_GITHUB_TOKEN` |
| Anthropic Key | `KIT_ANTHROPIC_TOKEN` |
| OpenAI Key | `KIT_OPENAI_TOKEN` |
| Google Key | `KIT_GOOGLE_API_KEY` |

## Supported LLM Providers

Kit review supports multiple LLM providers:

- **Anthropic Claude** - High-quality analysis with `claude-sonnet-4-20250514`
- **OpenAI GPT** - Reliable performance with `gpt-4.1-2025-04-14`
- **Google Gemini** - Great models like `gemini-2.5-flash`
- **Ollama** - Free local models like `qwen2.5-coder:latest`

### Cost Tracking

Kit review includes comprehensive cost tracking for all supported LLM providers:

- **Anthropic Claude**: Accurate token counting via API response metadata
- **OpenAI GPT**: Accurate token counting via API response metadata  
- **Google Gemini**: Accurate token counting via usage_metadata and count_tokens API
- **Ollama**: Free (estimated token counts for consistency)

Costs are calculated using real-time pricing and displayed after each review.
