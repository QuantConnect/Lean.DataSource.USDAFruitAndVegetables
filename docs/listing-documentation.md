# USDA Fruit and Vegetable Prices Documentation

## Overview

USDA ERS retail price estimates for 150+ commonly consumed fresh and processed fruits and vegetables. Includes price per pound/pint and normalized price per edible cup equivalent.


## Data Properties

| Property | Type | Description |
|----------|------|-------------|
| `AverageRetailPrice` | `decimal` | Average retail price per unit (pound or pint). |
| `Unit` | `PriceUnit` | Unit of measure for `AverageRetailPrice` (`per_pound`, `per_pint`, or `unknown`). |
| `PreparationYieldFactor` | `decimal` | Fraction of product that is edible after preparation (0.0–1.0). |
| `CupEquivalentSize` | `decimal` | Size of one edible cup equivalent. |
| `CupEquivalentUnit` | `CupEquivalentUnit` | Unit of measure for `CupEquivalentSize` (`pounds`, `pints`, `fluid_ounces`, or `unknown`). |
| `PricePerCupEquivalent` | `decimal` | Normalized price per edible cup equivalent (this is the `Value`). |


## Usage

### Adding the Data

#### C#
```csharp
public class MyAlgorithm : QCAlgorithm
{
    public override void Initialize()
    {

        // Each produce + form combination is its own data series (symbol), for example: Apples.Fresh
        AddData<USDAFruitAndVegetables>(USDAFruitAndVegetables.Apples.Fresh, Resolution.Daily);

    }
}
```

#### Python
```python
class MyAlgorithm(QCAlgorithm):
    def initialize(self):

        # Each produce + form combination is its own data series (symbol), for example: Apples.Fresh
        self.add_data(USDAFruitAndVegetables, USDAFruitAndVegetables.Apples.Fresh, Resolution.DAILY)

```

### Accessing the Data

#### C#
```csharp
public override void OnData(Slice slice)
{
    var data = slice.Get<USDAFruitAndVegetables>();
    foreach (var kvp in data)
    {
        var symbol = kvp.Key;
        var point = kvp.Value;

        Log($"{symbol}: {point}");

    }
}
```

#### Python
```python
def on_data(self, slice):
    data = slice.get(USDAFruitAndVegetables)
    for symbol, point in data.items():

        self.log(f"{symbol}: {point}")

```



## Data Source Details

| Attribute | Value |
|-----------|-------|
| Data Source ID | 0 |
| Resolution | Daily |
| Timezone | Utc |
| Requires Mapping | False |
| Sparse Data | True |

## Data Coverage

- **Start Date**: 2013-01-01
- **End Date**: 2023-01-01
- **Asset Coverage**: 191 series (produce + form combinations)
- **Data Density**: 4.09 rows/series on average; annual points by year: {2013: 159, 2016: 157, 2020: 155, 2022: 155, 2023: 155}
- **Data Process Duration**: 25.91s
- **Update Process Duration**: TBD

## Data Processing

The processor generates per-series CSV files under `alternative/usda/fruitandvegetables/` (for example, `apples_fresh.csv`).

**CSV Row Format:**
```
yyyyMMdd,AverageRetailPrice,Unit,PreparationYieldFactor,CupEquivalentSize,CupEquivalentUnit,PricePerCupEquivalent
```

See the repository README for configuration options and processing instructions.
