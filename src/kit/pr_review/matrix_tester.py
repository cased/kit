"""Comprehensive matrix testing system for PR reviews."""

import json
import statistics
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union, cast

from .agentic_reviewer import AgenticPRReviewer
from .config import GitHubConfig, LLMConfig, LLMProvider, ReviewConfig
from .reviewer import PRReviewer
from .validator import validate_review_quality


@dataclass
class TestResult:
    """Result of a single test run."""

    pr_url: str
    mode: str  # 'standard', 'agentic'
    model: str
    provider: str
    success: bool
    cost: float
    duration: float
    review_content: str
    structural_score: float
    structural_issues: List[str]
    structural_metrics: Dict[str, Any]
    opus_score: Optional[float] = None
    opus_feedback: Optional[str] = None
    error: Optional[str] = None


@dataclass
class MatrixTestSuite:
    """Complete test suite results."""

    test_runs: List[TestResult]
    summary_stats: Dict[str, Any]
    cost_analysis: Dict[str, Any]
    quality_rankings: Dict[str, Any]
    recommendations: List[str]


class MatrixTester:
    """Comprehensive matrix testing for PR review quality and cost analysis."""

    def __init__(self, base_config: ReviewConfig):
        self.base_config = base_config
        self.test_results: List[TestResult] = []

        # Define test matrix - using latest Claude 4 models
        self.models = [
            (LLMProvider.ANTHROPIC, "claude-opus-4-20250514", "Claude 4 Opus"),
            (LLMProvider.ANTHROPIC, "claude-sonnet-4-20250514", "Claude 4 Sonnet"),
            (LLMProvider.ANTHROPIC, "claude-3-5-sonnet-20241022", "Claude 3.5 Sonnet"),
            (LLMProvider.ANTHROPIC, "claude-3-5-haiku-20241022", "Claude 3.5 Haiku"),
            (LLMProvider.OPENAI, "gpt-4o", "GPT-4o"),
            (LLMProvider.OPENAI, "gpt-4o-mini", "GPT-4o Mini"),
            (LLMProvider.OPENAI, "gpt-4-turbo", "GPT-4 Turbo"),
        ]

        self.modes = [("standard", "Standard"), ("agentic", "Agentic")]

    def create_config(self, provider: LLMProvider, model: str) -> ReviewConfig:
        """Create config for specific provider/model combination."""
        # Copy base config
        github_config = GitHubConfig(token=self.base_config.github.token, base_url=self.base_config.github.base_url)

        # Determine API key
        if provider == LLMProvider.ANTHROPIC:
            api_key = self.base_config.llm.api_key if self.base_config.llm.provider == provider else None
            if not api_key:
                import os

                api_key = os.getenv("KIT_ANTHROPIC_TOKEN")
        else:
            api_key = self.base_config.llm.api_key if self.base_config.llm.provider == provider else None
            if not api_key:
                import os

                api_key = os.getenv("KIT_OPENAI_TOKEN")

        if not api_key:
            raise ValueError(f"No API key available for {provider.value}")

        llm_config = LLMConfig(
            provider=provider,
            model=model,
            api_key=api_key,
            max_tokens=self.base_config.llm.max_tokens,
        )

        return ReviewConfig(
            github=github_config,
            llm=llm_config,
            post_as_comment=False,  # Never post during testing
            clone_for_analysis=self.base_config.clone_for_analysis,
            cache_repos=self.base_config.cache_repos,
        )

    def run_single_test(
        self, pr_url: str, mode: str, provider: LLMProvider, model: str, display_name: str
    ) -> TestResult:
        """Run a single test configuration."""
        print(f"\n🔧 Testing: {display_name} ({mode} mode)")

        # Create config for this model
        config = self.create_config(provider, model)

        try:
            start_time = time.time()
            cost = 0.0
            reviewer: Union[PRReviewer, AgenticPRReviewer]  # Explicitly type the reviewer

            if mode == "standard":
                print("   📝 Running STANDARD review...")
                reviewer = PRReviewer(config)
                review = reviewer.review_pr(pr_url)
                cost = reviewer.cost_tracker.breakdown.llm_cost_usd
            elif mode == "agentic":
                print(f"   🤖 Running AGENTIC review (max {self.base_config.agentic_max_turns} turns)...")
                agentic_reviewer = AgenticPRReviewer(config)
                agentic_reviewer.max_turns = 8  # Budget setting for testing
                review = agentic_reviewer.review_pr_agentic(pr_url)
                cost = agentic_reviewer.cost_tracker.breakdown.llm_cost_usd
                reviewer = agentic_reviewer  # For later use
            else:
                raise ValueError(f"Unknown mode: {mode}")

            duration = time.time() - start_time
            print(f"   ⏱️  Review completed in {duration:.1f}s")
            print(f"   💰 Cost: ${cost:.4f}")
            print(f"   📝 Review length: {len(review):,} characters")

            # Get structural validation
            try:
                print("   🔍 Running quality validation...")
                # Get PR data for validation
                standard_reviewer = PRReviewer(config)
                owner, repo, pr_number = standard_reviewer.parse_pr_url(pr_url)
                files = standard_reviewer.get_pr_files(owner, repo, pr_number)
                pr_diff = standard_reviewer.get_pr_diff(owner, repo, pr_number)
                changed_files = [f["filename"] for f in files]

                validation = validate_review_quality(review, pr_diff, changed_files)

                result = TestResult(
                    pr_url=pr_url,
                    mode=mode,
                    model=model,
                    provider=provider.value,
                    success=True,
                    cost=cost,
                    duration=duration,
                    review_content=review,
                    structural_score=validation.score,
                    structural_issues=validation.issues,
                    structural_metrics=validation.metrics,
                )

                print(
                    f"   ✅ SUCCESS | Quality: {validation.score:.2f}/1.0 | Cost: ${cost:.3f} | Time: {duration:.1f}s"
                )
                if validation.issues:
                    print(
                        f"   ⚠️  Quality Issues: {', '.join(validation.issues[:2])}{'...' if len(validation.issues) > 2 else ''}"
                    )
                print(f"   📊 Metrics: {validation.metrics}")
                print("")  # Add spacing
                return result

            except Exception as e:
                print(f"   ⚠️  Review succeeded but validation failed: {e}")

                result = TestResult(
                    pr_url=pr_url,
                    mode=mode,
                    model=model,
                    provider=provider.value,
                    success=True,
                    cost=cost,
                    duration=duration,
                    review_content=review,
                    structural_score=0.0,
                    structural_issues=[f"Validation failed: {e}"],
                    structural_metrics={},
                )
                print("   ✅ Review completed but validation failed")
                print("")  # Add spacing
                return result

        except Exception as e:
            duration = time.time() - start_time
            print(f"   ❌ FAILED after {duration:.1f}s: {e}")
            print("")  # Add spacing

            return TestResult(
                pr_url=pr_url,
                mode=mode,
                model=model,
                provider=provider.value,
                success=False,
                cost=0.0,
                duration=duration,
                review_content="",
                structural_score=0.0,
                structural_issues=[],
                structural_metrics={},
                error=str(e),
            )

    def run_matrix_test(self, pr_urls: List[str], include_opus_judging: bool = True) -> MatrixTestSuite:
        """Run comprehensive matrix test across all combinations."""
        print("🔬 Starting Matrix Test")
        print(f"📋 Testing: {len(pr_urls)} PRs x {len(self.modes)} modes x {len(self.models)} models")
        print(f"🧠 Opus judging: {'Enabled' if include_opus_judging else 'Disabled'}")
        print("=" * 80)

        total_combinations = len(pr_urls) * len(self.modes) * len(self.models)
        current_combination = 0
        total_cost = 0.0
        successful_tests = 0
        failed_tests = 0

        start_time = time.time()

        for pr_url in pr_urls:
            print(f"\n📝 PR: {pr_url}")
            print(f"📊 Progress Overview: {current_combination}/{total_combinations} tests completed")
            print(f"💰 Running Total Cost: ${total_cost:.4f}")
            print(f"✅ Successful: {successful_tests} | ❌ Failed: {failed_tests}")
            print("-" * 60)

            for mode_id, mode_name in self.modes:
                print(f"\n🎯 {mode_name} Mode:")
                mode_start_time = time.time()
                mode_cost = 0.0
                mode_success = 0
                mode_failed = 0

                for provider, model, display_name in self.models:
                    current_combination += 1
                    progress = (current_combination / total_combinations) * 100
                    elapsed = time.time() - start_time

                    print(
                        f"  📍 [{current_combination}/{total_combinations}] ({progress:.1f}%) | Elapsed: {elapsed / 60:.1f}m"
                    )

                    result = self.run_single_test(pr_url, mode_id, provider, model, display_name)
                    self.test_results.append(result)

                    # Update running totals
                    if result.success:
                        successful_tests += 1
                        mode_success += 1
                        total_cost += result.cost
                        mode_cost += result.cost
                    else:
                        failed_tests += 1
                        mode_failed += 1

                mode_duration = time.time() - mode_start_time
                print(f"🏁 {mode_name} Mode Complete:")
                print(f"   ⏱️  Duration: {mode_duration / 60:.1f} minutes")
                print(f"   💰 Mode Cost: ${mode_cost:.4f}")
                print(f"   ✅ Success: {mode_success}/{len(self.models)} | ❌ Failed: {mode_failed}/{len(self.models)}")

                # Show ETA if we have enough data
                if current_combination > 3:
                    avg_time_per_test = elapsed / current_combination
                    remaining_tests = total_combinations - current_combination
                    eta_seconds = remaining_tests * avg_time_per_test
                    print(f"   ⏰ ETA: {eta_seconds / 60:.1f} minutes remaining")
                print("")

        # Print final summary before judging
        total_elapsed = time.time() - start_time
        print("\n🎉 All Reviews Complete!")
        print(f"⏱️  Total Time: {total_elapsed / 60:.1f} minutes")
        print(f"💰 Total Cost: ${total_cost:.4f}")
        print(
            f"✅ Successful: {successful_tests}/{total_combinations} ({successful_tests / total_combinations * 100:.1f}%)"
        )
        if failed_tests > 0:
            print(f"❌ Failed: {failed_tests}/{total_combinations} ({failed_tests / total_combinations * 100:.1f}%)")

        # Run Opus judging if requested
        if include_opus_judging:
            print("\n" + "=" * 60)
            print("🧠 Running Opus Quality Assessment...")
            judging_start_time = time.time()
            self._run_opus_judging()
            judging_duration = time.time() - judging_start_time
            print(f"🏛️  Judging completed in {judging_duration:.1f}s")

        # Generate analysis
        print("\n📊 Generating Final Analysis...")
        analysis_start_time = time.time()
        suite = self._generate_analysis()
        analysis_duration = time.time() - analysis_start_time
        print(f"📈 Analysis completed in {analysis_duration:.1f}s")

        grand_total_time = time.time() - start_time
        print("\n🎉 Matrix Test Complete!")
        print(f"📊 Generated {len(self.test_results)} test results")
        print(f"⏱️  Grand Total Time: {grand_total_time / 60:.1f} minutes")
        print(f"💰 Grand Total Cost: ${total_cost:.4f}")

        # Show quick insights
        if successful_tests > 0:
            avg_cost = total_cost / successful_tests
            print(f"📈 Average cost per test: ${avg_cost:.4f}")

            # Show best structural scores
            best_structural = max(
                (r for r in self.test_results if r.success), key=lambda x: x.structural_score, default=None
            )
            if best_structural:
                print(
                    f"🏆 Best structural score: {best_structural.structural_score:.2f} - {best_structural.provider} {best_structural.model} ({best_structural.mode})"
                )

            # Show cheapest successful test
            cheapest = min((r for r in self.test_results if r.success), key=lambda x: x.cost, default=None)
            if cheapest:
                print(
                    f"💎 Cheapest test: ${cheapest.cost:.4f} - {cheapest.provider} {cheapest.model} ({cheapest.mode})"
                )

            # Show any Opus scores if available
            opus_tests = [r for r in self.test_results if r.opus_score is not None]
            if opus_tests:
                best_opus = max(opus_tests, key=lambda x: x.opus_score if x.opus_score is not None else 0)
                print(
                    f"🧠 Best Opus score: {best_opus.opus_score}/10 - {best_opus.provider} {best_opus.model} ({best_opus.mode})"
                )
                avg_opus = sum(r.opus_score for r in opus_tests if r.opus_score is not None) / len(opus_tests)
                print(f"📊 Average Opus score: {avg_opus:.1f}/10 across {len(opus_tests)} reviews")

        return suite

    def _run_opus_judging(self):
        """Use Claude Opus to judge review quality."""
        print("🧠 Calling Claude Opus as quality judge...")

        try:
            import os

            import anthropic

            api_key = os.getenv("KIT_ANTHROPIC_TOKEN")
            if not api_key:
                print("⚠️  No Anthropic API key for Opus judging")
                return

            client = anthropic.Anthropic(api_key=api_key)

            # Group successful results by PR for judging
            by_pr = {}
            for result in self.test_results:
                if result.success:
                    if result.pr_url not in by_pr:
                        by_pr[result.pr_url] = []
                    by_pr[result.pr_url].append(result)

            for pr_url, pr_results in by_pr.items():
                print(f"  📝 Judging reviews for {pr_url}...")
                print(f"     🎯 {len(pr_results)} reviews to judge")

                # Check if we're testing Claude 4 Opus to avoid self-evaluation
                has_opus_4 = any(result.model == "claude-opus-4-20250514" for result in pr_results)

                if has_opus_4:
                    # Use OpenAI GPT-4o to judge Claude 4 Opus
                    judge_model = "gpt-4o"
                    judge_name = "OpenAI GPT-4o"
                    judge_provider = "openai"
                    print(f"    🤖 Using {judge_name} as judge (avoiding Claude 4 Opus self-evaluation)")
                else:
                    # Use Claude 4 Opus for all other models
                    judge_model = "claude-opus-4-20250514"
                    judge_name = "Claude 4 Opus"
                    judge_provider = "anthropic"
                    print(f"    🏆  Using {judge_name} as judge")

                # Show what we're judging
                for i, result in enumerate(pr_results, 1):
                    print(f"    📋 Review {i}: {result.provider} {result.model} ({result.mode} mode)")

                # Create judging prompt
                reviews_text = ""
                for i, result in enumerate(pr_results, 1):
                    reviews_text += f"\n**Review {i}: {result.provider} {result.model} ({result.mode} mode)**\n"
                    reviews_text += result.review_content + "\n---\n"

                judging_prompt = f"""Rate these {len(pr_results)} code reviews for the same PR on a 1-10 scale. Be critical but fair.

PR: {pr_url}

{reviews_text}

For each review, provide:
- Score (1-10)
- Brief reasoning (2-3 sentences)

Format as JSON:
{{"reviews": [
  {{"review_number": 1, "score": 8, "reasoning": "Good analysis but missed X"}},
  {{"review_number": 2, "score": 6, "reasoning": "Shallow review, missed Y"}}
]}}"""

                try:
                    print(f"    🤔 {judge_name} is evaluating {len(pr_results)} reviews...")

                    if judge_provider == "anthropic":
                        # Use Anthropic client
                        response = client.messages.create(
                            model=judge_model,
                            max_tokens=2000,
                            messages=[{"role": "user", "content": judging_prompt}],
                        )
                        content = response.content[0].text
                    else:
                        # Use OpenAI client for judging Claude 4 Opus
                        import os

                        import openai

                        openai_api_key = os.getenv("KIT_OPENAI_TOKEN") or os.getenv("OPENAI_API_KEY")
                        if not openai_api_key:
                            print("    ⚠️  No OpenAI API key for GPT-4o judging")
                            continue

                        openai_client = openai.OpenAI(api_key=openai_api_key)
                        # GPT-5 models use max_completion_tokens instead of max_tokens
                        completion_params: Dict[str, Any] = {
                            "model": judge_model,
                            "messages": [{"role": "user", "content": judging_prompt}],
                        }
                        if "gpt-5" in judge_model.lower():
                            completion_params["max_completion_tokens"] = 2000
                        else:
                            completion_params["max_tokens"] = 2000

                        response = openai_client.chat.completions.create(**completion_params)
                        content = response.choices[0].message.content

                    print(f"    ✅ {judge_name} completed evaluation")

                    # Try to extract JSON
                    import re

                    json_match = re.search(r"\{.*\}", content, re.DOTALL)
                    if json_match:
                        try:
                            judgment = json.loads(json_match.group())

                            # Apply scores to results and show them
                            for i, review_judgment in enumerate(judgment.get("reviews", [])):
                                if i < len(pr_results):
                                    score = review_judgment.get("score", 0)
                                    reasoning = review_judgment.get("reasoning", "")
                                    pr_results[i].opus_score = score
                                    pr_results[i].opus_feedback = reasoning

                                    model_name = (
                                        f"{pr_results[i].provider} {pr_results[i].model} ({pr_results[i].mode})"
                                    )
                                    print(f"    📊 {model_name}: {score}/10 - {reasoning}")

                            print(f"    ✅ Successfully judged {len(judgment.get('reviews', []))} reviews")

                        except json.JSONDecodeError:
                            print(f"    ⚠️  Failed to parse {judge_name} judgment JSON")
                    else:
                        print(f"    ⚠️  No JSON found in {judge_name} response")

                except Exception as e:
                    print(f"    ❌ {judge_name} judging failed: {e}")

                print("")  # Add spacing between PRs

        except ImportError:
            print("⚠️  Anthropic package not available for Opus judging")
        except Exception as e:
            print(f"❌ Opus judging setup failed: {e}")

    def _generate_analysis(self) -> MatrixTestSuite:
        """Generate comprehensive analysis of test results."""

        # Filter successful results
        successful = [r for r in self.test_results if r.success]

        if not successful:
            return MatrixTestSuite(
                test_runs=self.test_results,
                summary_stats={"error": "No successful test runs"},
                cost_analysis={},
                quality_rankings={},
                recommendations=["All tests failed - check configuration"],
            )

        # Summary statistics
        total_cost = sum(r.cost for r in successful)
        avg_cost = total_cost / len(successful)
        avg_duration = sum(r.duration for r in successful) / len(successful)
        avg_structural_score = sum(r.structural_score for r in successful) / len(successful)

        # Cost analysis by mode and model
        cost_by_mode: Dict[str, List[float]] = {}
        cost_by_model: Dict[str, List[float]] = {}

        for result in successful:
            # By mode
            if result.mode not in cost_by_mode:
                cost_by_mode[result.mode] = []
            cost_by_mode[result.mode].append(result.cost)

            # By model
            model_key = f"{result.provider}:{result.model}"
            if model_key not in cost_by_model:
                cost_by_model[model_key] = []
            cost_by_model[model_key].append(result.cost)

        # Calculate averages
        cost_analysis = {
            "by_mode": {
                mode: {
                    "avg_cost": statistics.mean(costs),
                    "min_cost": min(costs),
                    "max_cost": max(costs),
                    "count": len(costs),
                }
                for mode, costs in cost_by_mode.items()
            },
            "by_model": {
                model: {
                    "avg_cost": statistics.mean(costs),
                    "min_cost": min(costs),
                    "max_cost": max(costs),
                    "count": len(costs),
                }
                for model, costs in cost_by_model.items()
            },
        }

        # Quality rankings
        quality_rankings = {}

        # Structural scores
        if any(r.structural_score > 0 for r in successful):
            structural_scores: Dict[str, List[float]] = {}
            for result in successful:
                key = f"{result.provider}:{result.model}:{result.mode}"
                if key not in structural_scores:
                    structural_scores[key] = []
                structural_scores[key].append(result.structural_score)

            quality_rankings["structural"] = {key: statistics.mean(scores) for key, scores in structural_scores.items()}

        # Opus scores
        opus_results = [r for r in successful if r.opus_score is not None]
        if opus_results:
            opus_scores: Dict[str, List[float]] = {}
            for result in opus_results:
                key = f"{result.provider}:{result.model}:{result.mode}"
                if key not in opus_scores:
                    opus_scores[key] = []
                # Cast to float since we've already filtered for non-None values
                opus_scores[key].append(cast(float, result.opus_score))

            quality_rankings["opus"] = {key: statistics.mean(scores) for key, scores in opus_scores.items()}

        # Generate recommendations
        recommendations = self._generate_recommendations(successful, cost_analysis, quality_rankings)

        summary_stats = {
            "total_tests": len(self.test_results),
            "successful_tests": len(successful),
            "failed_tests": len(self.test_results) - len(successful),
            "total_cost": total_cost,
            "average_cost": avg_cost,
            "average_duration": avg_duration,
            "average_structural_score": avg_structural_score,
            "opus_judged_tests": len(opus_results),
        }

        return MatrixTestSuite(
            test_runs=self.test_results,
            summary_stats=summary_stats,
            cost_analysis=cost_analysis,
            quality_rankings=quality_rankings,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self, successful: List[TestResult], cost_analysis: Dict, quality_rankings: Dict
    ) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []

        # Cost recommendations
        if "by_mode" in cost_analysis:
            mode_costs = [(mode, data["avg_cost"]) for mode, data in cost_analysis["by_mode"].items()]
            mode_costs.sort(key=lambda x: x[1])

            cheapest_mode = mode_costs[0][0]
            most_expensive_mode = mode_costs[-1][0]

            recommendations.append(f"💰 Most cost-effective mode: {cheapest_mode} (avg ${mode_costs[0][1]:.3f})")
            recommendations.append(f"💸 Most expensive mode: {most_expensive_mode} (avg ${mode_costs[-1][1]:.3f})")

        # Quality recommendations
        if "opus" in quality_rankings:
            opus_scores = [(key, score) for key, score in quality_rankings["opus"].items()]
            opus_scores.sort(key=lambda x: x[1], reverse=True)

            if opus_scores:
                best = opus_scores[0]
                recommendations.append(f"🏆 Highest Opus quality: {best[0]} (score: {best[1]:.1f}/10)")

        # Value recommendations (quality/cost ratio)
        if "opus" in quality_rankings and "by_model" in cost_analysis:
            value_scores = []
            for key, quality in quality_rankings["opus"].items():
                # Extract model from key for cost lookup
                parts = key.split(":")
                if len(parts) >= 2:
                    model_key = ":".join(parts[:2])
                    if model_key in cost_analysis["by_model"]:
                        cost = cost_analysis["by_model"][model_key]["avg_cost"]
                        if cost > 0:
                            value = quality / cost  # Quality per dollar
                            value_scores.append((key, value, quality, cost))

            if value_scores:
                value_scores.sort(key=lambda x: x[1], reverse=True)
                best_value = value_scores[0]
                recommendations.append(
                    f"💎 Best value: {best_value[0]} (quality {best_value[2]:.1f} for ${best_value[3]:.3f})"
                )

        return recommendations

    def save_results(self, filepath: str):
        """Save test results to JSON file."""
        # Convert results to serializable format
        serializable_results = []
        for result in self.test_results:
            result_dict = asdict(result)
            serializable_results.append(result_dict)

        with open(filepath, "w") as f:
            json.dump(
                {
                    "test_results": serializable_results,
                    "timestamp": time.time(),
                    "summary": {
                        "total_tests": len(self.test_results),
                        "successful_tests": len([r for r in self.test_results if r.success]),
                    },
                },
                f,
                indent=2,
            )

        print(f"💾 Results saved to {filepath}")

    def load_results(self, filepath: str):
        """Load test results from JSON file."""
        with open(filepath, "r") as f:
            data = json.load(f)

        self.test_results = []
        for result_dict in data["test_results"]:
            result = TestResult(**result_dict)
            self.test_results.append(result)

        print(f"📂 Loaded {len(self.test_results)} test results from {filepath}")


def main():
    """CLI for matrix testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Matrix testing for PR reviews")
    parser.add_argument("command", choices=["run", "analyze", "compare"])
    parser.add_argument("--pr-urls", nargs="+", help="PR URLs to test")
    parser.add_argument("--pr-list", help="File containing PR URLs")
    parser.add_argument("--config", help="Config file path")
    parser.add_argument("--output", help="Output file for results")
    parser.add_argument("--load", help="Load previous results file")
    parser.add_argument("--no-opus", action="store_true", help="Skip Opus judging")

    args = parser.parse_args()

    # Load config
    config = ReviewConfig.from_file(args.config) if args.config else ReviewConfig.from_file()
    tester = MatrixTester(config)

    if args.command == "run":
        # Get PR URLs
        if args.pr_urls:
            pr_urls = args.pr_urls
        elif args.pr_list:
            with open(args.pr_list, "r") as f:
                pr_urls = [line.strip() for line in f if line.strip()]
        else:
            print("❌ Need --pr-urls or --pr-list")
            return

        # Run matrix test
        suite = tester.run_matrix_test(pr_urls, include_opus_judging=not args.no_opus)

        # Save results
        if args.output:
            tester.save_results(args.output)

        # Print summary
        print("\n📊 MATRIX TEST SUMMARY")
        print("=" * 40)
        for key, value in suite.summary_stats.items():
            if isinstance(value, float):
                print(f"{key}: {value:.3f}")
            else:
                print(f"{key}: {value}")

        print("\n💡 RECOMMENDATIONS")
        for rec in suite.recommendations:
            print(f"  {rec}")

    elif args.command == "analyze":
        if not args.load:
            print("❌ Need --load for analyze command")
            return

        tester.load_results(args.load)
        suite = tester._generate_analysis()

        print(f"📊 Analysis complete - {len(suite.recommendations)} recommendations")

    elif args.command == "compare":
        print("🔄 Compare mode - load multiple result files and compare")
        # TODO: Implement comparison between different test runs


if __name__ == "__main__":
    main()
