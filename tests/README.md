# DFR Application Test Suite

Comprehensive unit and integration tests for the modularized DFR (Drone as First Responder) planning application.

## Test Structure

### Coverage Analysis Tests (`test_coverage_analysis.py`)
Tests for RF propagation and path loss calculations:
- **TestElevationEstimation**: Elevation caching and retrieval
- **TestClutterLoss**: Land-use based clutter loss modeling
- **TestTerrainBlockage**: Terrain diffraction and blockage calculations
- **TestPathLossAdvanced**: Comprehensive path loss models
- **TestPathLossIntegration**: Realistic link budget scenarios

### Export Handlers Tests (`test_export_handlers.py`)
Tests for data export utilities:
- **TestBuildCorrectedExport**: DataFrame cleaning and export preparation
- **TestExportIntegration**: Real-world merged dataset handling

### Station Generation Tests (`test_station_generation.py`)
Tests for drone station placement:
- **TestMakeRandomStations**: Random station generation with KMeans fallback
- **TestGenerateStationsFromCalls**: Call-based station optimization
- **TestStationGenerationIntegration**: Realistic geographic distributions

### Search Utilities Tests (`test_search_utils.py`)
Tests for address and facility search:
- **TestNormalizeSearchText**: Text normalization for search
- **TestIsProbablyCoordinate**: Coordinate detection
- **TestScoreLocationMatch**: Location ranking and scoring
- **TestDeduplicateCandidates**: Candidate deduplication
- **TestSearchUtilsIntegration**: Complete search workflows

### Propagation Utilities Tests (`test_propagation_utils.py`)
Tests for RF propagation helper functions:
- **TestElevationCaching**: Elevation cache management
- **TestGreatCircleDistance**: Geographic distance calculations
- **TestFresnelRadius**: Fresnel zone calculations
- **TestFreeSpacePathLoss**: Friis equation implementation
- **TestTerrainBlockageLoss**: Knife-edge diffraction models
- **TestClutterLoss**: Clutter loss estimation
- **TestPropagationIntegration**: Complete RF budget analysis

## Running Tests

### Run All Tests
```bash
pytest
# or
./run_tests.sh
```

### Run Specific Test File
```bash
pytest tests/test_coverage_analysis.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_coverage_analysis.py::TestPathLossAdvanced -v
```

### Run Specific Test
```bash
pytest tests/test_coverage_analysis.py::TestPathLossAdvanced::test_path_loss_increases_with_distance -v
```

### Run with Coverage Report
```bash
pytest --cov=modules --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest -k "path_loss" -v
```

### Run Only Fast Tests
```bash
pytest -m "not slow" -v
```

## Test Categories

Tests are marked with pytest markers for selective running:

- `@pytest.mark.unit` - Unit tests for individual functions
- `@pytest.mark.integration` - Integration tests across modules
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.coverage` - Coverage analysis tests
- `@pytest.mark.search` - Search utility tests
- `@pytest.mark.propagation` - RF propagation tests
- `@pytest.mark.export` - Export handler tests
- `@pytest.mark.stations` - Station generation tests

## Test Coverage Goals

| Module | Target Coverage | Status |
|--------|-----------------|--------|
| `modules/coverage_analysis.py` | 95%+ | ✓ |
| `modules/export_handlers.py` | 95%+ | ✓ |
| `modules/station_generation.py` | 85%+ | ✓ |
| `modules/search_utils.py` | 95%+ | ✓ |
| `modules/propagation_utils.py` | 95%+ | ✓ |

## Dependencies

Tests require pytest and the application's dependencies:

```bash
pip install pytest pytest-cov
```

## Test Design Principles

1. **Isolation**: Each test is independent and can run in any order
2. **Clarity**: Test names clearly describe what is being tested
3. **Comprehensive**: Tests cover happy paths, edge cases, and error conditions
4. **Realistic**: Integration tests use realistic data and scenarios
5. **Fast**: Unit tests run quickly; only integration tests may be marked slow

## Adding New Tests

When adding new functionality:

1. Create test file following pattern: `test_<module_name>.py`
2. Create test class for each major function: `Test<FunctionName>`
3. Add docstrings explaining what is being tested
4. Test both normal cases and edge cases
5. Run full test suite to ensure no regressions

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:

```bash
pytest --cov=modules --cov-report=xml --junitxml=test-results.xml
```

## Known Limitations

- External API tests (OSM, HIFLD) are mocked or skipped
- Tests don't cover Streamlit UI components (use Streamlit testing framework for that)
- Some tests use fixed random seeds for deterministic behavior
- Elevation data uses mock model, not real DEM

## Future Enhancements

- Add performance benchmarking tests
- Add property-based tests with Hypothesis
- Add mutation testing to verify test quality
- Add snapshot testing for complex data structures
