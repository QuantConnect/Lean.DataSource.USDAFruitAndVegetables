
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
using NodaTime;
using QuantConnect.Data;
using QuantConnect.Logging;
using static QuantConnect.StringExtensions;

namespace QuantConnect.DataSource
{
    /// <summary>
    /// USDAFruitAndVegetables - USDA ERS retail price estimates for 150+ commonly consumed fresh and
    /// processed fruits and vegetables. Includes price per pound/pint and normalized price per edible
    /// cup equivalent.
    /// </summary>
    /// <remarks>
    /// Data source ID: 0
    /// </remarks>
    public partial class USDAFruitAndVegetables : BaseData
    {
        /// <summary>
        /// Data source ID for USDA FruitAndVegetables
        /// </summary>
        public const int DataSourceId = 0;


        /// <summary>
        /// Average retail price per unit (pound or pint)
        /// </summary>
        public decimal AverageRetailPrice { get; set; }


        /// <summary>
        /// Unit of measure - PerPound (solids) or PerPint (juice)
        /// </summary>
        public PriceUnit Unit { get; set; }


        /// <summary>
        /// Fraction of product that is edible after preparation (0.0-1.0)
        /// </summary>
        public decimal PreparationYieldFactor { get; set; }


        /// <summary>
        /// Size of one edible cup equivalent
        /// </summary>
        public decimal CupEquivalentSize { get; set; }

        /// <summary>
        /// Unit of measure for <see cref="CupEquivalentSize"/>
        /// </summary>
        public CupEquivalentUnit CupEquivalentUnit { get; set; }


        /// <summary>
        /// Normalized price per edible cup equivalent (comparable across forms)
        /// </summary>
        public decimal PricePerCupEquivalent { get; set; }


        /// <summary>
        /// Returns the primary value (PricePerCupEquivalent).
        /// </summary>
        /// <remarks>
        /// PricePerCupEquivalent is chosen over AverageRetailPrice because it enables
        /// meaningful cross-form comparisons. A pound of fresh apples and a pint of
        /// apple juice have different retail prices, but their price-per-cup-equivalent
        /// normalizes for edible portion size, making cost comparisons valid across
        /// fresh, canned, dried, and juice forms of the same product.
        /// </remarks>
        public override decimal Value => PricePerCupEquivalent;

        /// <summary>
        /// Gets or sets the end time for the data point (Daily data => Time + 1 day)
        /// </summary>
        public override DateTime EndTime
        {
            get => Time.Add(TimeSpan.FromDays(1));
            set => Time = value.AddDays(-1);
        }




        /// <summary>
        /// Return the URL source for the data
        /// </summary>
        /// <param name="config">Subscription data config</param>
        /// <param name="date">Date of the data</param>
        /// <param name="isLiveMode">Is this live mode</param>
        /// <returns>Subscription data source</returns>
        public override SubscriptionDataSource GetSource(SubscriptionDataConfig config, DateTime date, bool isLiveMode)
        {

            var seriesCode = config.Symbol.Value.ToLowerInvariant();
            var source = Path.Combine(
                Globals.DataFolder,
                "alternative",
                "usda",
                "fruitandvegetables",
                $"{seriesCode}.csv"
            );

            return new SubscriptionDataSource(source, SubscriptionTransportMedium.LocalFile, FileFormat.Csv);

        }


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
            try
            {
                if (string.IsNullOrWhiteSpace(line))
                {
                    throw new FormatException("USDAFruitAndVegetables.Reader(): Encountered empty line.");
                }

                var columns = line.Split(',');

                if (columns.Length != CsvSchema.ColumnCount)
                {
                    throw new FormatException(
                        $"USDAFruitAndVegetables.Reader(): Invalid CSV format, expected {CsvSchema.ColumnCount} columns but got {columns.Length}."
                    );
                }
                var dateText = columns[CsvSchema.DateIndex].Trim();
                if (dateText.Length != 8 || !long.TryParse(dateText, out _))
                {
                    throw new FormatException(
                        "USDAFruitAndVegetables.Reader(): Invalid CSV format, expected yyyyMMdd date in first column."
                    );
                }

                var time = Parse.DateTimeExact(dateText, "yyyyMMdd");
                var unit = ParsePriceUnit(columns[CsvSchema.UnitIndex]);
                if (unit == PriceUnit.Unknown)
                {
                    throw new FormatException(
                        $"USDAFruitAndVegetables.Reader(): Unknown price unit '{columns[CsvSchema.UnitIndex]}'."
                    );
                }

                var cupEquivalentUnit = ParseCupEquivalentUnit(columns[CsvSchema.CupEquivalentUnitIndex]);
                if (cupEquivalentUnit == CupEquivalentUnit.Unknown)
                {
                    throw new FormatException(
                        $"USDAFruitAndVegetables.Reader(): Unknown cup equivalent unit '{columns[CsvSchema.CupEquivalentUnitIndex]}'."
                    );
                }

                return new USDAFruitAndVegetables()
                {
                    Symbol = config.Symbol,
                    Time = time,
                    AverageRetailPrice = Parse.Decimal(columns[CsvSchema.AverageRetailPriceIndex]),
                    Unit = unit,
                    PreparationYieldFactor = Parse.Decimal(columns[CsvSchema.PreparationYieldFactorIndex]),
                    CupEquivalentSize = Parse.Decimal(columns[CsvSchema.CupEquivalentSizeIndex]),
                    CupEquivalentUnit = cupEquivalentUnit,
                    PricePerCupEquivalent = Parse.Decimal(columns[CsvSchema.PricePerCupEquivalentIndex]),
                };
            }
            catch (Exception ex)
            {
                var series = config.Symbol?.Value ?? "unknown";
                Log.Error($"USDAFruitAndVegetables.Reader(): Error parsing {series} line: {line}, Exception: {ex.Message}");
                throw;
            }

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
            return new USDAFruitAndVegetables()
            {
                Symbol = Symbol,
                Time = Time,
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

            return Invariant($"{Symbol} - AverageRetailPrice: {AverageRetailPrice}, Unit: {Unit}, PreparationYieldFactor: {PreparationYieldFactor}, CupEquivalentSize: {CupEquivalentSize}, CupEquivalentUnit: {CupEquivalentUnit}, PricePerCupEquivalent: {PricePerCupEquivalent}");

        }

        private static PriceUnit ParsePriceUnit(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return PriceUnit.Unknown;
            }

            var normalized = value.Trim().ToLowerInvariant();
            return normalized switch
            {
                CsvSchema.PriceUnitPerPound => PriceUnit.PerPound,
                CsvSchema.PriceUnitPerPint => PriceUnit.PerPint,
                CsvSchema.PriceUnitUnknown => PriceUnit.Unknown,
                _ => PriceUnit.Unknown
            };
        }

        private static CupEquivalentUnit ParseCupEquivalentUnit(string value)
        {
            if (string.IsNullOrWhiteSpace(value))
            {
                return CupEquivalentUnit.Unknown;
            }

            var normalized = value.Trim().ToLowerInvariant();
            return normalized switch
            {
                CsvSchema.CupEquivalentUnitPounds => CupEquivalentUnit.Pounds,
                CsvSchema.CupEquivalentUnitPints => CupEquivalentUnit.Pints,
                CsvSchema.CupEquivalentUnitFluidOunces => CupEquivalentUnit.FluidOunces,
                CsvSchema.CupEquivalentUnitUnknown => CupEquivalentUnit.Unknown,
                _ => CupEquivalentUnit.Unknown
            };
        }
    }
}
