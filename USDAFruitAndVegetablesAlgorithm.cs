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

using QuantConnect.Algorithm;
using QuantConnect.Data;

namespace QuantConnect.DataSource
{
    /// <summary>
    /// Example algorithm using USDAFruitAndVegetables data
    /// </summary>
    public class USDAFruitAndVegetablesAlgorithm : QCAlgorithm
    {

        private QuantConnect.Symbol _customDataSymbol = QuantConnect.Symbol.Empty;

        /// <summary>
        /// Initialise the data and resolution required.
        /// </summary>
        public override void Initialize()
        {
            SetStartDate(2020, 1, 1);
            SetEndDate(2020, 12, 31);
            SetCash(100000);


            // Add standalone custom data
            // Each produce + form combination is its own data series (symbol), for example: Apples.Fresh
            _customDataSymbol = AddData<USDAFruitAndVegetables>(USDAFruitAndVegetables.Apples.Fresh, Resolution.Daily).Symbol;


            // Request historical data for warmup
            var history = History<USDAFruitAndVegetables>(_customDataSymbol, 30, Resolution.Daily);
            Debug($"Received {history.Count()} historical data points");
        }

        /// <summary>
        /// OnData event is the primary entry point for your algorithm.
        /// </summary>
        /// <param name="slice">Slice object keyed by symbol containing the stock data</param>
        public override void OnData(Slice slice)
        {
            // Get the custom data
            var dataPoints = slice.Get<USDAFruitAndVegetables>();

            foreach (var kvp in dataPoints)
            {
                var symbol = kvp.Key;
                var data = kvp.Value;

                // Log the data

                Log($"{Time}: {symbol} - {data}");

            }
        }

        /// <summary>
        /// End of algorithm run event
        /// </summary>
        public override void OnEndOfAlgorithm()
        {
            Debug($"Algorithm completed. Final portfolio value: {Portfolio.TotalPortfolioValue}");
        }
    }
}
