class CostGenerator:
	"""Estimate API cost for different OpenAI models.

	This class provides a simple interface to compute estimated cost
	given the number of input tokens, output tokens, and a model name.

	Supported models and their default prices (USD per 1,000 tokens):
	- gpt-5: 0.06 (input), 0.12 (output)
	- gpt-5-mini: 0.002 (input), 0.004 (output)
	- gpt-4.1: 0.03 (input), 0.06 (output)

	The values above are defaults and should be kept up-to-date by
	the caller if pricing changes.
	"""

	DEFAULT_PRICING = {
		"gpt-5": {"input_per_1k": 0.06, "output_per_1k": 0.12},
		"gpt-5-mini": {"input_per_1k": 0.002, "output_per_1k": 0.004},
		"gpt-4.1": {"input_per_1k": 0.03, "output_per_1k": 0.06},
	}

	def __init__(self, pricing: dict | None = None):
		"""Create a CostGenerator.

		Args:
			pricing: Optional mapping of model -> {"input_per_1k": float, "output_per_1k": float}.
				When omitted, `DEFAULT_PRICING` will be used.
		"""
		self.pricing = pricing or dict(self.DEFAULT_PRICING)

	def estimate(self, input_tokens: int, output_tokens: int, model: str) -> dict:
		"""Estimate cost for a single API call.

		Args:
			input_tokens: Number of input tokens used.
			output_tokens: Number of output tokens generated.
			model: Model name (one of the supported keys).

		Returns:
			A dictionary with breakdown: input_tokens, output_tokens, model,
			input_cost, output_cost, total_cost.

		Raises:
			ValueError: If tokens are negative or model is not supported.
		"""
		if input_tokens < 0 or output_tokens < 0:
			raise ValueError("Token counts must be non-negative integers.")

		model = model.lower()
		if model not in self.pricing:
			raise ValueError(f"Unsupported model '{model}'. Supported: {', '.join(self.pricing.keys())}")

		rates = self.pricing[model]
		input_cost = (input_tokens / 1000.0) * rates["input_per_1k"]
		output_cost = (output_tokens / 1000.0) * rates["output_per_1k"]
		total = input_cost + output_cost

		return {
			"model": model,
			"input_tokens": int(input_tokens),
			"output_tokens": int(output_tokens),
			"input_cost": round(input_cost, 8),
			"output_cost": round(output_cost, 8),
			"total_cost": round(total, 8),
		}


