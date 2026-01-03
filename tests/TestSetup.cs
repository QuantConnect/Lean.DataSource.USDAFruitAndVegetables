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

using NUnit.Framework;
using QuantConnect.Configuration;
using QuantConnect.Logging;

namespace QuantConnect.DataSource.Tests
{
    /// <summary>
    /// Test assembly setup and teardown
    /// </summary>
    [SetUpFixture]
    public class TestSetup
    {
        /// <summary>
        /// One-time setup for the entire test assembly
        /// </summary>
        [OneTimeSetUp]
        public void GlobalSetup()
        {
            // Initialize logging
            Log.LogHandler = new ConsoleLogHandler();
            Log.DebuggingEnabled = true;

            // Load configuration
            Config.Reset();

            // Set up any global configuration needed for tests
            // Additional configuration can be added here when required
        }

        /// <summary>
        /// One-time teardown for the entire test assembly
        /// </summary>
        [OneTimeTearDown]
        public void GlobalTeardown()
        {
            // Clean up any global resources
        }
    }
}
