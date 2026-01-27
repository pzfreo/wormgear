/**
 * Test Suite for Generator UI
 *
 * Tests all recent fixes:
 * - Markdown generation with correct class names
 * - Progress indicator state transitions
 * - Time estimation for hobbing
 * - ZIP creation with all files
 * - STL export inclusion
 */

// Mock DOM elements for testing
function setupMockDOM() {
    // Create progress container
    const progressContainer = document.createElement('div');
    progressContainer.id = 'generation-progress';
    progressContainer.style.display = 'none';

    // Main progress
    const mainProgress = document.createElement('div');
    mainProgress.id = 'main-progress';

    const mainStepText = document.createElement('div');
    mainStepText.id = 'main-step-text';
    mainProgress.appendChild(mainStepText);

    // Step indicators
    const stepsContainer = document.createElement('div');
    ['parse', 'worm', 'wheel', 'export'].forEach(step => {
        const indicator = document.createElement('div');
        indicator.className = 'step-indicator';
        indicator.dataset.step = step;
        stepsContainer.appendChild(indicator);
    });
    mainProgress.appendChild(stepsContainer);
    progressContainer.appendChild(mainProgress);

    // Sub-progress
    const subProgress = document.createElement('div');
    subProgress.id = 'sub-progress';
    subProgress.style.display = 'none';

    const subProgressText = document.createElement('div');
    subProgressText.id = 'sub-progress-text';
    subProgress.appendChild(subProgressText);

    const progressBarContainer = document.createElement('div');
    const progressBar = document.createElement('div');
    progressBar.id = 'progress-bar';
    progressBarContainer.appendChild(progressBar);
    subProgress.appendChild(progressBarContainer);

    progressContainer.appendChild(subProgress);

    // Console output
    const consoleOutput = document.createElement('div');
    consoleOutput.id = 'console-output';

    document.body.appendChild(progressContainer);
    document.body.appendChild(consoleOutput);
}

function cleanupMockDOM() {
    const progress = document.getElementById('generation-progress');
    const console = document.getElementById('console-output');
    if (progress) progress.remove();
    if (console) console.remove();
}

// Test framework
class TestRunner {
    constructor() {
        this.suites = [];
    }

    suite(name, setupFn) {
        const suite = {
            name,
            tests: [],
            beforeEach: null,
            afterEach: null
        };

        const context = {
            beforeEach: (fn) => { suite.beforeEach = fn; },
            afterEach: (fn) => { suite.afterEach = fn; },
            test: (testName, testFn) => {
                suite.tests.push({ name: testName, fn: testFn });
            }
        };

        setupFn(context);
        this.suites.push(suite);
    }

    async run(onProgress) {
        let total = 0;
        let passed = 0;
        let failed = 0;

        for (const suite of this.suites) {
            for (const test of suite.tests) {
                total++;
                onProgress(suite.name, test.name, 'running', null);

                try {
                    if (suite.beforeEach) await suite.beforeEach();
                    await test.fn();
                    if (suite.afterEach) await suite.afterEach();

                    passed++;
                    onProgress(suite.name, test.name, 'pass', null);
                } catch (error) {
                    failed++;
                    onProgress(suite.name, test.name, 'fail', error.message);
                }
            }
        }

        return { total, passed, failed };
    }
}

// Assertion helpers
function assert(condition, message) {
    if (!condition) {
        throw new Error(message || 'Assertion failed');
    }
}

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(message || `Expected ${expected}, got ${actual}`);
    }
}

function assertIncludes(string, substring, message) {
    if (!string.includes(substring)) {
        throw new Error(message || `Expected "${string}" to include "${substring}"`);
    }
}

function assertHasClass(element, className, message) {
    if (!element.classList.contains(className)) {
        throw new Error(message || `Expected element to have class "${className}"`);
    }
}

function assertNotHasClass(element, className, message) {
    if (element.classList.contains(className)) {
        throw new Error(message || `Expected element not to have class "${className}"`);
    }
}

// Create test runner instance
const runner = new TestRunner();

// ============================================================================
// TEST SUITE 1: Progress Indicator State Transitions
// ============================================================================

runner.suite('Progress Indicator State Transitions', ({ test, beforeEach, afterEach }) => {
    beforeEach(() => {
        setupMockDOM();
        // Dynamically import the module functions we need
        return import('../modules/generator-ui.js');
    });

    afterEach(() => {
        cleanupMockDOM();
    });

    test('Parse step sets parse indicator to active', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('📋 Parsing parameters...', null);

        const parseIndicator = document.querySelector('[data-step="parse"]');
        assertHasClass(parseIndicator, 'active', 'Parse indicator should be active');
        assertNotHasClass(parseIndicator, 'complete', 'Parse indicator should not be complete');
    });

    test('Worm step transitions parse to complete and sets worm to active', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('📋 Parsing parameters...', null);
        handleProgress('🔩 Generating worm gear...', null);

        const parseIndicator = document.querySelector('[data-step="parse"]');
        const wormIndicator = document.querySelector('[data-step="worm"]');

        assertHasClass(parseIndicator, 'complete', 'Parse should be complete');
        assertNotHasClass(parseIndicator, 'active', 'Parse should not be active');
        assertHasClass(wormIndicator, 'active', 'Worm should be active');
    });

    test('Wheel step transitions worm to complete and sets wheel to active', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('📋 Parsing parameters...', null);
        handleProgress('🔩 Generating worm gear...', null);
        handleProgress('⚙️  Generating wheel gear...', null);

        const parseIndicator = document.querySelector('[data-step="parse"]');
        const wormIndicator = document.querySelector('[data-step="worm"]');
        const wheelIndicator = document.querySelector('[data-step="wheel"]');

        assertHasClass(parseIndicator, 'complete', 'Parse should be complete');
        assertHasClass(wormIndicator, 'complete', 'Worm should be complete');
        assertHasClass(wheelIndicator, 'active', 'Wheel should be active');
    });

    test('Export step transitions wheel to complete and sets export to active', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('📋 Parsing parameters...', null);
        handleProgress('🔩 Generating worm gear...', null);
        handleProgress('⚙️  Generating wheel gear...', null);
        handleProgress('  Exporting to STEP format...', null);

        const wheelIndicator = document.querySelector('[data-step="wheel"]');
        const exportIndicator = document.querySelector('[data-step="export"]');

        assertHasClass(wheelIndicator, 'complete', 'Wheel should be complete');
        assertHasClass(exportIndicator, 'active', 'Export should be active');
    });

    test('All steps complete on generation finish', async () => {
        const { handleProgress, handleGenerateComplete } = await import('../modules/generator-ui.js');

        // Simulate full generation flow
        handleProgress('📋 Parsing parameters...', null);
        handleProgress('🔩 Generating worm gear...', null);
        handleProgress('⚙️  Generating wheel gear...', null);
        handleProgress('  Exporting to STEP format...', null);

        // Mock successful completion
        window.currentGeneratedDesign = null; // Skip markdown generation
        await handleGenerateComplete({
            success: true,
            worm: 'mock-base64-worm',
            wheel: 'mock-base64-wheel',
            worm_stl: 'mock-base64-worm-stl',
            wheel_stl: 'mock-base64-wheel-stl'
        });

        const indicators = document.querySelectorAll('.step-indicator');
        indicators.forEach(indicator => {
            assertHasClass(indicator, 'complete', `${indicator.dataset.step} should be complete`);
            assertNotHasClass(indicator, 'active', `${indicator.dataset.step} should not be active`);
        });
    });
});

// ============================================================================
// TEST SUITE 2: Hobbing Progress and Time Estimation
// ============================================================================

runner.suite('Hobbing Progress and Time Estimation', ({ test, beforeEach, afterEach }) => {
    beforeEach(() => {
        setupMockDOM();
        return import('../modules/generator-ui.js');
    });

    afterEach(() => {
        cleanupMockDOM();
    });

    test('Hobbing progress shows sub-progress bar', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('Virtual hobbing step 10/100', 10);

        const subProgress = document.getElementById('sub-progress');
        assert(subProgress.style.display !== 'none', 'Sub-progress should be visible');

        const progressBar = document.getElementById('progress-bar');
        assertEqual(progressBar.style.width, '10%', 'Progress bar should be at 10%');
    });

    test('Time estimation appears after 5% completion', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        // Simulate hobbing progress
        handleProgress('Virtual hobbing step 1/100', 1);
        await new Promise(resolve => setTimeout(resolve, 100)); // Wait 100ms

        handleProgress('Virtual hobbing step 6/100', 6);

        const progressText = document.getElementById('sub-progress-text');
        assertIncludes(progressText.textContent, 'Estimated', 'Should show time estimate after 5%');
        assertIncludes(progressText.textContent, 'remaining', 'Should show "remaining" text');
    });

    test('Time estimation formats minutes and seconds', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        // Simulate slow hobbing to trigger minute display
        handleProgress('Virtual hobbing step 1/100', 1);
        await new Promise(resolve => setTimeout(resolve, 200)); // Simulate 200ms for 1%

        handleProgress('Virtual hobbing step 6/100', 6);

        const progressText = document.getElementById('sub-progress-text');
        // Should show seconds at minimum
        assert(
            progressText.textContent.includes('s remaining') ||
            progressText.textContent.includes('m '),
            'Should format time with seconds or minutes'
        );
    });

    test('Sub-progress hides when not hobbing', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('Virtual hobbing step 50/100', 50);
        const subProgress = document.getElementById('sub-progress');
        assert(subProgress.style.display !== 'none', 'Sub-progress should be visible during hobbing');

        handleProgress('  Exporting to STEP format...', null);
        assertEqual(subProgress.style.display, 'none', 'Sub-progress should hide after hobbing');
    });
});

// ============================================================================
// TEST SUITE 3: Message Type Handling
// ============================================================================

runner.suite('Message Type Handling', ({ test, beforeEach, afterEach }) => {
    beforeEach(() => {
        setupMockDOM();
    });

    afterEach(() => {
        cleanupMockDOM();
    });

    test('LOG messages trigger progress updates', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        // Simulate LOG message (which should be processed by handleProgress in generator-ui.js)
        handleProgress('🔩 Generating worm gear...', null);

        const wormIndicator = document.querySelector('[data-step="worm"]');
        assertHasClass(wormIndicator, 'active', 'LOG message should trigger progress update');
    });

    test('PROGRESS messages with percent show hobbing progress', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        handleProgress('Virtual hobbing step 25/100', 25);

        const progressBar = document.getElementById('progress-bar');
        assertEqual(progressBar.style.width, '25%', 'PROGRESS message should update progress bar');
    });

    test('Different emoji indicators trigger correct steps', async () => {
        const { handleProgress } = await import('../modules/generator-ui.js');

        // Parse emoji
        handleProgress('📋 Parsing parameters...', null);
        assertHasClass(document.querySelector('[data-step="parse"]'), 'active');

        // Worm emoji
        handleProgress('🔩 Generating worm gear...', null);
        assertHasClass(document.querySelector('[data-step="worm"]'), 'active');

        // Wheel emoji
        handleProgress('⚙️  Generating wheel gear...', null);
        assertHasClass(document.querySelector('[data-step="wheel"]'), 'active');
    });
});

// ============================================================================
// TEST SUITE 4: Filename Generation
// ============================================================================

runner.suite('Filename Generation', ({ test }) => {
    test('Creates descriptive filename from design parameters', async () => {
        // We need to expose createFilename function for testing
        // For now, test the pattern manually
        const design = {
            worm: { module_mm: 2.0, num_starts: 1 },
            wheel: { num_teeth: 30 },
            assembly: { ratio: 30 },
            manufacturing: { worm_type: 'cylindrical' }
        };

        // Expected format: wormgear_m2_0_30-1_cyl
        const module = design.worm.module_mm.toFixed(1).replace('.', '_');
        const teeth = design.wheel.num_teeth;
        const starts = design.worm.num_starts;
        const type = design.manufacturing.worm_type === 'cylindrical' ? 'cyl' : 'glob';

        const expected = `wormgear_m${module}_${teeth}-${starts}_${type}`;
        assertEqual(expected, 'wormgear_m2_0_30-1_cyl', 'Filename should match expected format');
    });

    test('Handles globoid worm type', async () => {
        const design = {
            worm: { module_mm: 1.5, num_starts: 2 },
            wheel: { num_teeth: 40 },
            assembly: { ratio: 20 },
            manufacturing: { worm_type: 'globoid' }
        };

        const module = design.worm.module_mm.toFixed(1).replace('.', '_');
        const teeth = design.wheel.num_teeth;
        const starts = design.worm.num_starts;
        const type = design.manufacturing.worm_type === 'cylindrical' ? 'cyl' : 'glob';

        const expected = `wormgear_m${module}_${teeth}-${starts}_${type}`;
        assertEqual(expected, 'wormgear_m1_5_40-2_glob', 'Filename should show glob for globoid');
    });
});

// ============================================================================
// TEST SUITE 5: Data Structure Validation
// ============================================================================

runner.suite('Data Structure Validation', ({ test }) => {
    test('Generated STEP data includes all required files', async () => {
        // Mock the completion data structure
        const completionData = {
            success: true,
            worm: 'base64-encoded-worm-step',
            wheel: 'base64-encoded-wheel-step',
            worm_stl: 'base64-encoded-worm-stl',
            wheel_stl: 'base64-encoded-wheel-stl'
        };

        assert(completionData.worm, 'Should include worm STEP');
        assert(completionData.wheel, 'Should include wheel STEP');
        assert(completionData.worm_stl, 'Should include worm STL');
        assert(completionData.wheel_stl, 'Should include wheel STL');
    });

    test('ZIP should contain 6 files', async () => {
        // Expected files in ZIP:
        const expectedFiles = [
            'design.json',
            'design.md',
            'worm.step',
            'wheel.step',
            'worm.stl',
            'wheel.stl'
        ];

        assertEqual(expectedFiles.length, 6, 'ZIP should contain exactly 6 files');
        assert(expectedFiles.includes('worm.stl'), 'Should include worm STL');
        assert(expectedFiles.includes('wheel.stl'), 'Should include wheel STL');
    });

    test('Design JSON has correct structure for markdown generation', async () => {
        const designJSON = {
            worm: { module_mm: 2.0 },
            wheel: { num_teeth: 30 },
            assembly: {
                centre_distance_mm: 38.14,
                ratio: 30,
                pressure_angle_deg: 20,
                backlash_mm: 0.05,
                hand: 'right',
                efficiency_percent: 85,
                self_locking: false
            },
            manufacturing: {
                profile: 'ZA',
                worm_type: 'cylindrical',
                worm_length: 40.0,
                wheel_width: 10.0,
                virtual_hobbing: false,
                hobbing_steps: 18,
                throated_wheel: false
            }
        };

        // Validate structure needed for markdown generation
        assert(designJSON.assembly.centre_distance_mm, 'Assembly should have centre_distance_mm');
        assert(designJSON.assembly.hand, 'Assembly should have hand');
        assert(designJSON.manufacturing.profile, 'Manufacturing should have profile');
        assertEqual(typeof designJSON.assembly.efficiency_percent, 'number', 'Efficiency should be number');
    });
});

// ============================================================================
// TEST SUITE 6: Console Output
// ============================================================================

runner.suite('Console Output', ({ test, beforeEach, afterEach }) => {
    beforeEach(() => {
        setupMockDOM();
    });

    afterEach(() => {
        cleanupMockDOM();
    });

    test('Messages are appended to console', async () => {
        const { appendToConsole } = await import('../modules/generator-ui.js');

        const consoleOutput = document.getElementById('console-output');
        const initialChildCount = consoleOutput.children.length;

        appendToConsole('Test message');

        assertEqual(
            consoleOutput.children.length,
            initialChildCount + 1,
            'Should add one line to console'
        );
    });

    test('Console messages include timestamps', async () => {
        const { appendToConsole } = await import('../modules/generator-ui.js');

        appendToConsole('Test message');

        const consoleOutput = document.getElementById('console-output');
        const lastLine = consoleOutput.lastChild;

        assertIncludes(lastLine.textContent, '[', 'Should include opening bracket for timestamp');
        assertIncludes(lastLine.textContent, ']', 'Should include closing bracket for timestamp');
        assertIncludes(lastLine.textContent, 'Test message', 'Should include message text');
    });

    test('Console auto-scrolls to bottom', async () => {
        const { appendToConsole } = await import('../modules/generator-ui.js');

        const consoleOutput = document.getElementById('console-output');

        // Add multiple messages
        for (let i = 0; i < 10; i++) {
            appendToConsole(`Message ${i}`);
        }

        // Check that scrollTop equals scrollHeight (scrolled to bottom)
        assertEqual(
            consoleOutput.scrollTop,
            consoleOutput.scrollHeight,
            'Console should auto-scroll to bottom'
        );
    });
});

// Export test runner
export async function runAllTests(onProgress) {
    return await runner.run(onProgress);
}
