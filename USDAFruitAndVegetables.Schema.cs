/*
 * This file is auto-generated. Do not edit by hand.
 * Source: datasources/USDAFruitAndVegetables/datasource-fruitandvegetables.yaml
 * Generator: datasources/USDAFruitAndVegetables/scripts/generate_schema_artifacts.py
 */

using System.Runtime.Serialization;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;

namespace QuantConnect.DataSource
{
    public partial class USDAFruitAndVegetables
    {
        internal static class CsvSchema
        {
            public const int ColumnCount = 7;
            public const int DateIndex = 0;
            public const int AverageRetailPriceIndex = 1;
            public const int UnitIndex = 2;
            public const int PreparationYieldFactorIndex = 3;
            public const int CupEquivalentSizeIndex = 4;
            public const int CupEquivalentUnitIndex = 5;
            public const int PricePerCupEquivalentIndex = 6;

            public const string PriceUnitUnknown = "unknown";
            public const string PriceUnitPerPound = "per_pound";
            public const string PriceUnitPerPint = "per_pint";

            public const string CupEquivalentUnitUnknown = "unknown";
            public const string CupEquivalentUnitPounds = "pounds";
            public const string CupEquivalentUnitPints = "pints";
            public const string CupEquivalentUnitFluidOunces = "fluid_ounces";
        }
    }

    [JsonConverter(typeof(StringEnumConverter))]
    public enum PriceUnit
    {
        [EnumMember(Value = "unknown")]
        Unknown,

        [EnumMember(Value = "per_pound")]
        PerPound,

        [EnumMember(Value = "per_pint")]
        PerPint,
    }

    [JsonConverter(typeof(StringEnumConverter))]
    public enum CupEquivalentUnit
    {
        [EnumMember(Value = "unknown")]
        Unknown,

        [EnumMember(Value = "pounds")]
        Pounds,

        [EnumMember(Value = "pints")]
        Pints,

        [EnumMember(Value = "fluid_ounces")]
        FluidOunces,
    }
}
