
def recursive_replace(node, replace_dict, num_iterations):
	if isinstance(node, dict):
		res = {}
		for k, v in node.items():
			res[k] = recursive_replace(v, replace_dict, num_iterations)

		return res
	elif isinstance(node, list):
		return [recursive_replace(x, replace_dict, num_iterations) for x in node]
	elif isinstance(node, str):
		res = node
		for k, v in replace_dict.items():
			value = v

			# Deal with values we need to unpack
			if isinstance(v, list):
				if len(v) <= num_iterations:
					raise Exception('Ran out of variables to unpack - ' \
						'Variable: {} | Iterations: {}'.format(k, num_iterations))

				value = v[num_iterations]

			res = res.replace("{{{}}}".format(k), str(value))

		return res
	else:
		return node


def calculator_eval(expr):
	whitelist = '+*/%-'
	if not any(char in whitelist or char.isdigit() for char in expr):
		return 0

	return eval(expr)