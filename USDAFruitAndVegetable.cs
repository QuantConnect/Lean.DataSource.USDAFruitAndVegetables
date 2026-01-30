
/*
 * QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
 * Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

using System.Diagnostics.CodeAnalysis;
using System.Runtime.Serialization;
using Newtonsoft.Json;
using Newtonsoft.Json.Converters;
using NodaTime;
using QuantConnect.Data;
using static QuantConnect.StringExtensions;

namespace QuantConnect.DataSource
{
    /// <summary>
    /// USDAFruitAndVegetable - Individual data point for USDA ERS retail price estimates.
    /// Contains price data for a specific product form (Fresh, Canned, Frozen, etc.).
    /// </summary>
    /// <remarks>
    /// This is the singular class representing one data row. Use <see cref="USDAFruitAndVegetables"/>
    /// (plural) as the subscription type, which aggregates multiple forms per product.
    /// </remarks>
    public partial class USDAFruitAndVegetable : BaseData
    {
        /// <summary>
        /// Product form identifier (e.g., "Fresh", "Canned", "Fresh - Florets").
        /// </summary>
        public string Form { get; set; } = string.Empty;


        /// <summary>
        /// Average retail price per unit (pound or pint).
        /// </summary>
        public decimal? AverageRetailPrice { get; set; }


        /// <summary>
        /// Unit of measure - PerPound (solids) or PerPint (juice).
        /// </summary>
        public PriceUnit? Unit { get; set; }


        /// <summary>
        /// Fraction of product that is edible after preparation (0.0-1.0).
        /// </summary>
        public decimal? PreparationYieldFactor { get; set; }


        /// <summary>
        /// Size of one edible cup equivalent.
        /// </summary>
        public decimal? CupEquivalentSize { get; set; }

        /// <summary>
        /// Unit of measure for <see cref="CupEquivalentSize"/>.
        /// </summary>
        public CupEquivalentUnit? CupEquivalentUnit { get; set; }


        /// <summary>
        /// Normalized price per edible cup equivalent (comparable across forms).
        /// </summary>
        public decimal? PricePerCupEquivalent { get; set; }


        /// <summary>
        /// Returns the primary value (PricePerCupEquivalent), or 0 if null.
        /// </summary>
        /// <remarks>
        /// PricePerCupEquivalent is chosen over AverageRetailPrice because it enables
        /// meaningful cross-form comparisons. A pound of fresh apples and a pint of
        /// apple juice have different retail prices, but their price-per-cup-equivalent
        /// normalizes for edible portion size, making cost comparisons valid across
        /// fresh, canned, dried, and juice forms of the same product.
        ///
        /// Returns 0 when PricePerCupEquivalent is null for chart compatibility.
        /// Check PricePerCupEquivalent.HasValue when null-awareness is needed.
        /// </remarks>
        public override decimal Value => PricePerCupEquivalent ?? 0m;


        /// <summary>
        /// Read and parse the data from a line
        /// </summary>
        /// <param name="config">Subscription data config</param>
        /// <param name="line">Line of data</param>
        /// <param name="date">Date of the data</param>
        /// <param name="isLiveMode">Is this live mode</param>
        /// <returns>Parsed data object</returns>
        [return: MaybeNull]
        public override BaseData Reader(SubscriptionDataConfig config, string line, DateTime date, bool isLiveMode)
        {

            if (string.IsNullOrWhiteSpace(line))
            {
                throw new FormatException("Encountered empty line");
            }

            var csv = line.Split(',');

            if (csv.Length != 8)
            {
                throw new FormatException(
                    $"Invalid CSV format, expected 8 columns but got {csv.Length}"
                );
            }

            var dateText = csv[0].Trim();
            if (dateText.Length != 8 || !long.TryParse(dateText, out _))
            {
                throw new FormatException(
                    "Invalid CSV format, expected yyyyMMdd date in first column"
                );
            }

            // yyyyMMdd[0], Form[1], AverageRetailPrice[2], Unit[3], PreparationYieldFactor[4], CupEquivalentSize[5], CupEquivalentUnit[6], PricePerCupEquivalent[7]
            // 20140101,Applesauce,1.0778249292591484,per_pound,1,0.54013254235295,pounds,0.5821683192521324

            return new USDAFruitAndVegetable()
            {
                Symbol = config.Symbol,
                Time = Parse.DateTimeExact(dateText, "yyyyMMdd"),
                Form = csv[1].Trim(),
                AverageRetailPrice = TryParseNullableDecimal(csv[2]),
                Unit = TryParsePriceUnit(csv[3]),
                PreparationYieldFactor = TryParseNullableDecimal(csv[4]),
                CupEquivalentSize = TryParseNullableDecimal(csv[5]),
                CupEquivalentUnit = TryParseCupEquivalentUnit(csv[6]),
                PricePerCupEquivalent = TryParseNullableDecimal(csv[7]),
            };
        }

        /// <summary>
        /// Indicates whether this data requires mapping
        /// </summary>
        /// <returns>True if requires mapping, false otherwise</returns>
        public override bool RequiresMapping()
        {
            return false;
        }

        /// <summary>
        /// Indicates whether this is sparse data
        /// </summary>
        /// <returns>True if sparse, false otherwise</returns>
        public override bool IsSparseData()
        {
            return true;
        }

        /// <summary>
        /// Gets the default resolution for this data
        /// </summary>
        /// <returns>The default resolution</returns>
        public override Resolution DefaultResolution()
        {
            return Resolution.Daily;
        }

        /// <summary>
        /// Gets the supported resolutions for this data
        /// </summary>
        /// <returns>List of supported resolutions</returns>
        public override List<Resolution> SupportedResolutions()
        {
            return DailyResolution;
        }

        /// <summary>
        /// Gets the data timezone for this data
        /// </summary>
        /// <returns>The timezone</returns>
        public override DateTimeZone DataTimeZone()
        {
            return TimeZones.Utc;
        }

        /// <summary>
        /// Creates a clone of this instance
        /// </summary>
        /// <returns>A clone of this instance</returns>
        public override BaseData Clone()
        {
            return new USDAFruitAndVegetable()
            {
                Symbol = Symbol,
                Time = Time,
                Form = Form,
                AverageRetailPrice = AverageRetailPrice,
                Unit = Unit,
                PreparationYieldFactor = PreparationYieldFactor,
                CupEquivalentSize = CupEquivalentSize,
                CupEquivalentUnit = CupEquivalentUnit,
                PricePerCupEquivalent = PricePerCupEquivalent,
            };
        }

        /// <summary>
        /// Returns a string representation of this data
        /// </summary>
        /// <returns>String representation</returns>
        public override string ToString()
        {

            return Invariant($"{Symbol} [{Form}] - AverageRetailPrice: {AverageRetailPrice}, Unit: {Unit}, PreparationYieldFactor: {PreparationYieldFactor}, CupEquivalentSize: {CupEquivalentSize}, CupEquivalentUnit: {CupEquivalentUnit}, PricePerCupEquivalent: {PricePerCupEquivalent}");

        }

        /// <summary>
        /// Parse a nullable decimal from CSV. Empty string returns null.
        /// </summary>
        private static decimal? TryParseNullableDecimal(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            if (!decimal.TryParse(value.Trim(), out var result))
            {
                throw new FormatException($"Invalid decimal value '{value}'");
            }
            return result;
        }

        /// <summary>
        /// Parse price unit. Returns null if empty string.
        /// </summary>
        private static PriceUnit? TryParsePriceUnit(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            return value.Trim().ToLowerInvariant() switch
            {
                "per_pound" => PriceUnit.PerPound,
                "per_pint" => PriceUnit.PerPint,
                _ => null
            };
        }

        /// <summary>
        /// Parse cup equivalent unit. Returns null if empty string.
        /// </summary>
        private static DataSource.CupEquivalentUnit? TryParseCupEquivalentUnit(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return null;
            }

            return value.Trim().ToLowerInvariant() switch
            {
                "pounds" => DataSource.CupEquivalentUnit.Pounds,
                "pints" => DataSource.CupEquivalentUnit.Pints,
                "fluid_ounces" => DataSource.CupEquivalentUnit.FluidOunces,
                _ => null
            };
        }
    }

    /// <summary>
    /// Price unit for USDA retail price data.
    /// </summary>
    [JsonConverter(typeof(StringEnumConverter))]
    public enum PriceUnit
    {
        /// <summary>Price per pound (used for solid products)</summary>
        [EnumMember(Value = "per_pound")]
        PerPound,

        /// <summary>Price per pint (used for juice products)</summary>
        [EnumMember(Value = "per_pint")]
        PerPint,
    }

    /// <summary>
    /// Cup equivalent unit for USDA nutritional data.
    /// </summary>
    [JsonConverter(typeof(StringEnumConverter))]
    public enum CupEquivalentUnit
    {
        /// <summary>Cup equivalent measured in pounds</summary>
        [EnumMember(Value = "pounds")]
        Pounds,

        /// <summary>Cup equivalent measured in pints</summary>
        [EnumMember(Value = "pints")]
        Pints,

        /// <summary>Cup equivalent measured in fluid ounces</summary>
        [EnumMember(Value = "fluid_ounces")]
        FluidOunces,
    }
}
