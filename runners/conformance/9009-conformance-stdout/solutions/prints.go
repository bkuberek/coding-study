package conformance_stdout

import "fmt"

func shout(text string) string {
	fmt.Println(text)
	return text
}
