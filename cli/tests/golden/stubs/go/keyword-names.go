// Keyword Names. Statement: .statements/keyword-names.md. Run: cstudy test keyword-names

package keyword_names

type Robot struct{}

func NewRobot(ref int) *Robot {
	return &Robot{}
}

func (r *Robot) Move(steps int) int {
	panic("not implemented")
}

func (r *Robot) Loop(match int) {
	panic("not implemented")
}
