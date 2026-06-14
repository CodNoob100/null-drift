import json
import tiktoken
from faker import Faker
import matplotlib.pyplot as plt
import matplotlib.style as style


def generate_agent_response(fake: Faker):
    return {
        "reasoning": fake.paragraph(nb_sentences=3),
        "tool_name": fake.word() + "_tool",
        "parameters": {
            "arg1": fake.pystr(),
            "arg2": fake.random_int(),
            "metadata": {"source": fake.url(), "timestamp": fake.iso8601()},
        },
        "raw_error_trace": f'Error in module {fake.file_path()}:\nTraceback (most recent call last):\n  File "{fake.file_name()}", line {fake.random_int(1, 500)}, in {fake.word()}\n{fake.sentence()}',
        "action_timestamp": fake.iso8601(),
    }


def main():
    fake = Faker()
    # Use cl100k_base which is used by OpenAI's gpt-3.5/gpt-4
    enc = tiktoken.get_encoding("cl100k_base")

    TURNS = 100
    BASE_PROMPT_TOKENS = 500
    NULL_DRIFT_PROJECTION_TOKENS = 200
    NULL_DRIFT_FIXED_TOKENS = BASE_PROMPT_TOKENS + NULL_DRIFT_PROJECTION_TOKENS

    standard_context_sizes = []
    null_drift_context_sizes = []

    standard_cumulative_billed = 0
    null_drift_cumulative_billed = 0

    current_history_tokens = 0

    for turn in range(1, TURNS + 1):
        # Generate fake JSON response
        response_data = generate_agent_response(fake)
        response_json = json.dumps(response_data)

        # Count tokens for this specific turn's JSON
        turn_tokens = len(enc.encode(response_json))

        # Standard Method: Append to history
        current_history_tokens += turn_tokens
        standard_context_size = BASE_PROMPT_TOKENS + current_history_tokens

        standard_context_sizes.append(standard_context_size)
        standard_cumulative_billed += standard_context_size

        # Null-Drift Method: Fixed O(1) state
        null_drift_context_sizes.append(NULL_DRIFT_FIXED_TOKENS)
        null_drift_cumulative_billed += NULL_DRIFT_FIXED_TOKENS

    # --- Plotting ---
    plt.style.use("dark_background")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left Chart: Context Window Size Per Turn
    turns_x = list(range(1, TURNS + 1))
    ax1.plot(
        turns_x,
        standard_context_sizes,
        color="#ff4b4b",
        label="Standard (Append-Only)",
        linewidth=2,
    )
    ax1.plot(
        turns_x,
        null_drift_context_sizes,
        color="#00ff9d",
        label="null-drift (O(1) State)",
        linewidth=2,
    )
    ax1.set_title("Context Window Size Per Turn", fontsize=14, pad=15)
    ax1.set_xlabel("Turn Number", fontsize=12)
    ax1.set_ylabel("Tokens in Context", fontsize=12)
    ax1.grid(color="#2a2a2a", linestyle="--", alpha=0.7)
    ax1.legend(loc="upper left", frameon=False)

    # Right Chart: Total Cumulative Tokens Billed
    labels = ["Standard", "null-drift"]
    values = [standard_cumulative_billed, null_drift_cumulative_billed]
    colors = ["#ff4b4b", "#00ff9d"]
    bars = ax2.bar(labels, values, color=colors, width=0.5, alpha=0.9)
    ax2.set_title(
        f"Total Cumulative Tokens Billed (After {TURNS} Turns)", fontsize=14, pad=15
    )
    ax2.set_ylabel("Total Tokens", fontsize=12)

    # Add value labels on top of bars
    for bar in bars:
        height = bar.get_height()
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + (max(values) * 0.02),
            f"{int(height):,}",
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
        )

    # Make styling minimal and modern
    for ax in [ax1, ax2]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#555555")
        ax.spines["left"].set_color("#555555")
        ax.tick_params(colors="#aaaaaa")

    plt.tight_layout()
    output_path = "docs/assets/token_diff_benchmark.png"
    plt.savefig(
        output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor()
    )
    print(f"Benchmark complete. Plot saved to {output_path}")


if __name__ == "__main__":
    main()
