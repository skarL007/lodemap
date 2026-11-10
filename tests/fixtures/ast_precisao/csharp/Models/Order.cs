namespace Shop.Models;

using Shop.Util;

public class Order
{
    string n = Strings.Up("pedido");
}

public record Line(int Q);
