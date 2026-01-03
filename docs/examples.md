# USDA FruitAndVegetables Examples

## Basic Usage Example

### C# Algorithm

```csharp
using QuantConnect.Data;
using QuantConnect.DataSource;

namespace QuantConnect.Algorithm.CSharp
{
    public class USDAFruitAndVegetablesExampleAlgorithm : QCAlgorithm
    {

        private Symbol _dataSymbol;

        public override void Initialize()
        {
            SetStartDate(2020, 1, 1);
            SetEndDate(2020, 12, 31);
            SetCash(100000);


            _dataSymbol = AddData<USDAFruitAndVegetables>(USDAFruitAndVegetables.Apples.Fresh, Resolution.Daily).Symbol;

        }

        public override void OnData(Slice slice)
        {
            var data = slice.Get<USDAFruitAndVegetables>();
            
            foreach (var kvp in data)
            {

                // Process data point
                Log($"{Time}: {kvp.Key} - {kvp.Value}");

            }
        }
    }
}
```

### Python Algorithm

```python
from AlgorithmImports import *

class USDAFruitAndVegetablesExampleAlgorithm(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2020, 12, 31)
        self.set_cash(100000)


        self.data_symbol = self.add_data(USDAFruitAndVegetables, USDAFruitAndVegetables.Apples.Fresh, Resolution.DAILY).symbol


    def on_data(self, slice):
        data = slice.get(USDAFruitAndVegetables)
        
        for symbol, point in data.items():

            # Process data point
            self.log(f"{self.time}: {symbol} - {point}")

```
