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
*/

using NodaTime;
using NUnit.Framework;
using QuantConnect.Data;

namespace QuantConnect.DataSource.Tests
{
    [TestFixture]
    public class USDAFruitAndVegetablesTests
    {
        private USDAFruitAndVegetables _instance = null!;
        private SubscriptionDataConfig _config = null!;

        [SetUp]
        public void SetUp()
        {
            _instance = new USDAFruitAndVegetables();
            _config = new SubscriptionDataConfig(
                typeof(USDAFruitAndVegetables),
                Symbol.Create(USDAFruitAndVegetables.Apples.Fresh, SecurityType.Base, Market.USA),
                Resolution.Daily,
                DateTimeZoneProviders.Tzdb["UTC"],
                DateTimeZoneProviders.Tzdb["UTC"],
                false,
                false,
                false
            );
        }

        [Test]
        public void ReaderReturnsValidData()
        {
            var line = "20200101,1.23,per_pound,0.9,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            var result = _instance.Reader(_config, line, date, false) as USDAFruitAndVegetables;

            Assert.That(result, Is.Not.Null);
            var data = result!;
            Assert.That(data.Symbol, Is.EqualTo(_config.Symbol));
            Assert.That(data.Time, Is.EqualTo(date));
            Assert.That(data.EndTime, Is.EqualTo(date.AddDays(1)));

            Assert.That(data.AverageRetailPrice, Is.EqualTo(1.23m));
            Assert.That(data.Unit, Is.EqualTo(PriceUnit.PerPound));
            Assert.That(data.PreparationYieldFactor, Is.EqualTo(0.9m));
            Assert.That(data.CupEquivalentSize, Is.EqualTo(0.25m));
            Assert.That(data.CupEquivalentUnit, Is.EqualTo(CupEquivalentUnit.Pounds));
            Assert.That(data.PricePerCupEquivalent, Is.EqualTo(0.50m));
            Assert.That(data.Value, Is.EqualTo(0.50m));
        }

        [Test]
        public void ReaderParsesSampleOutputLine()
        {
            var line = "20130101,1.5675153914496354,per_pound,0.9,0.24250848840336534,pounds,0.42237309792162286";
            var date = new DateTime(2013, 1, 1);

            var result = _instance.Reader(_config, line, date, false) as USDAFruitAndVegetables;

            Assert.That(result, Is.Not.Null);
            var data = result!;
            Assert.That(data.Time, Is.EqualTo(date));
            Assert.That(data.AverageRetailPrice, Is.EqualTo(1.5675153914496354m));
            Assert.That(data.Unit, Is.EqualTo(PriceUnit.PerPound));
            Assert.That(data.PreparationYieldFactor, Is.EqualTo(0.9m));
            Assert.That(data.CupEquivalentSize, Is.EqualTo(0.24250848840336534m));
            Assert.That(data.CupEquivalentUnit, Is.EqualTo(CupEquivalentUnit.Pounds));
            Assert.That(data.PricePerCupEquivalent, Is.EqualTo(0.42237309792162286m));
            Assert.That(data.Value, Is.EqualTo(0.42237309792162286m));
        }

        [Test]
        public void ReaderThrowsOnEmptyLine()
        {
            var date = new DateTime(2020, 1, 1);
            Assert.Throws<FormatException>(() => _instance.Reader(_config, " ", date, false));
        }

        [Test]
        public void ReaderThrowsOnInvalidColumnCount()
        {
            var line = "20200101,1.23,per_pound";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnInvalidDate()
        {
            var line = "2020-01-01,1.23,per_pound,0.9,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnUnknownPriceUnit()
        {
            var line = "20200101,1.23,unknown,0.9,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnUnknownCupEquivalentUnit()
        {
            var line = "20200101,1.23,per_pound,0.9,0.25,unknown,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnInvalidDayInDate()
        {
            // Per Constitution: Fail-fast - invalid day (32) should raise
            var line = "20200132,1.23,per_pound,0.9,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnNonNumericPrice()
        {
            // Per Constitution: Fail-fast - non-numeric price should raise
            var line = "20200101,abc,per_pound,0.9,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void ReaderThrowsOnNonNumericYieldFactor()
        {
            var line = "20200101,1.23,per_pound,invalid,0.25,pounds,0.50";
            var date = new DateTime(2020, 1, 1);

            Assert.Throws<FormatException>(() => _instance.Reader(_config, line, date, false));
        }

        [Test]
        public void GetSourceUsesSeriesCode()
        {
            var source = _instance.GetSource(_config, new DateTime(2020, 1, 1), false);

            Assert.That(
                source.Source,
                Does.EndWith(Path.Combine("alternative", "usda", "fruitandvegetables", $"{USDAFruitAndVegetables.Apples.Fresh}.csv"))
            );
            Assert.That(source.TransportMedium, Is.EqualTo(SubscriptionTransportMedium.LocalFile));
            Assert.That(source.Format, Is.EqualTo(FileFormat.Csv));
        }

        [Test]
        public void SupportedResolutionsIsDaily()
        {
            Assert.That(_instance.SupportedResolutions(), Is.EquivalentTo(new[] { Resolution.Daily }));
        }

        [Test]
        public void DataTimeZoneIsUtc()
        {
            Assert.That(_instance.DataTimeZone(), Is.EqualTo(TimeZones.Utc));
        }

        [Test]
        public void RequiresMappingReturnsFalse()
        {
            Assert.That(_instance.RequiresMapping(), Is.EqualTo(false));
        }

        [Test]
        public void IsSparseDataReturnsTrue()
        {
            Assert.That(_instance.IsSparseData(), Is.EqualTo(true));
        }

        [Test]
        public void DefaultResolutionIsDaily()
        {
            Assert.That(_instance.DefaultResolution(), Is.EqualTo(Resolution.Daily));
        }

        [Test]
        public void CloneReturnsValidCopy()
        {
            // Arrange
            _instance.Time = new DateTime(2020, 1, 1);
            _instance.EndTime = _instance.Time.AddDays(1);
            _instance.AverageRetailPrice = 1.23m;
            _instance.Unit = PriceUnit.PerPound;
            _instance.PreparationYieldFactor = 0.9m;
            _instance.CupEquivalentSize = 0.25m;
            _instance.CupEquivalentUnit = CupEquivalentUnit.Pounds;
            _instance.PricePerCupEquivalent = 0.50m;


            // Act
            var clone = _instance.Clone() as USDAFruitAndVegetables;

            // Assert
            Assert.That(clone, Is.Not.Null);
            var cloneData = clone!;
            Assert.That(cloneData, Is.Not.SameAs(_instance));
            Assert.That(cloneData.Time, Is.EqualTo(_instance.Time));
            Assert.That(cloneData.EndTime, Is.EqualTo(_instance.EndTime));
            Assert.That(cloneData.AverageRetailPrice, Is.EqualTo(_instance.AverageRetailPrice));
            Assert.That(cloneData.Unit, Is.EqualTo(_instance.Unit));
            Assert.That(cloneData.PreparationYieldFactor, Is.EqualTo(_instance.PreparationYieldFactor));
            Assert.That(cloneData.CupEquivalentSize, Is.EqualTo(_instance.CupEquivalentSize));
            Assert.That(cloneData.CupEquivalentUnit, Is.EqualTo(_instance.CupEquivalentUnit));
            Assert.That(cloneData.PricePerCupEquivalent, Is.EqualTo(_instance.PricePerCupEquivalent));

        }
    }
}
