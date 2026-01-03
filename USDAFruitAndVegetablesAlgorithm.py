# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from AlgorithmImports import *

class USDAFruitAndVegetablesAlgorithm(QCAlgorithm):
    """Example algorithm using USDAFruitAndVegetables data"""

    def initialize(self) -> None:
        """Initialize the algorithm"""
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2020, 12, 31)
        self.set_cash(100000)


        # Add standalone custom data
        # Each produce + form combination is its own data series (symbol), for example: Apples.Fresh
        self.custom_data_symbol = self.add_data(USDAFruitAndVegetables, USDAFruitAndVegetables.Apples.Fresh, Resolution.DAILY).symbol


        # Request historical data for warmup
        history = self.history(USDAFruitAndVegetables, self.custom_data_symbol, 30, Resolution.DAILY)
        self.debug(f"Received {len(history)} historical data points")

    def on_data(self, slice: Slice) -> None:
        """On data event handler"""
        # Get the custom data
        data_points = slice.get(USDAFruitAndVegetables)

        for symbol, data in data_points.items():
            # Log the data

            self.log(f"{self.time}: {symbol} - {data}")


    def on_end_of_algorithm(self) -> None:
        """End of algorithm event"""
        self.debug(f"Algorithm completed. Final portfolio value: {self.portfolio.total_portfolio_value}")
