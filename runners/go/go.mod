module cstudy

go 1.22

require github.com/shopspring/decimal v1.5.0

// Vendored (third_party/README.md): builds run with GOPROXY=off and never download a module.
replace github.com/shopspring/decimal => ./third_party/github.com/shopspring/decimal
