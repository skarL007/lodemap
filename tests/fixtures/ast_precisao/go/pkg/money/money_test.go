package money_test

import (
	"testing"

	"example.com/shop/internal/store"
	"example.com/shop/pkg/money"
)

func TestZero(t *testing.T) { _ = store.Nome + money.Zero }
