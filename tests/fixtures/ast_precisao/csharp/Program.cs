using System;
using System.IO;
using System.Linq;
using Shop.Models;
using Shop.Services;
using static Shop.Util.MathX;
using Alias = Shop.Models.Order;
using M = Shop.Models;
using Json = Newtonsoft.Json;
// using Shop.Util;
/* using Shop.Unused; */

namespace Shop.App
{
    class Program
    {
        static string texto = @"using Shop.Unused;
Unused";

        static void Main()
        {
            using var fluxo = new MemoryStream();
            using (var outro = new MemoryStream()) { }
            var o = new Alias();
            var c = new Customer();
            new OrderService();
            Sq(2);
            M.Line l = null;
        }
    }
}
