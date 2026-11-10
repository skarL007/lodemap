package main

import (
	"fmt"
	st "example.com/shop/internal/store"
	. "example.com/shop/internal/dot"
	_ "example.com/shop/internal/drivers"
	"example.com/shop/pkg/money"
	"example.com/shop2/other" // import "example.com/shop/internal/ghost"
	"github.com/google/uuid"
	"example.com/third/lib"
)

// import "example.com/shop/internal/ghost"
var cru = `
import "example.com/shop/internal/ghost"
`

func main() { fmt.Println(st.Nome, Ajuda(), money.Zero, other.X, uuid.New(), lib.Ola(), cru) }
