package rotate_image

func rotate(matrix [][]int) {
	n := len(matrix)
	for layer := 0; layer < n/2; layer++ {
		last := n - 1 - layer
		for offset := 0; offset < last-layer; offset++ {
			top := matrix[layer][layer+offset]
			// left -> top, bottom -> left, right -> bottom, top -> right
			matrix[layer][layer+offset] = matrix[last-offset][layer]
			matrix[last-offset][layer] = matrix[last][last-offset]
			matrix[last][last-offset] = matrix[layer+offset][last]
			matrix[layer+offset][last] = top
		}
	}
}
