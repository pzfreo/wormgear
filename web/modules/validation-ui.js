/**
 * Validation UI Module
 *
 * Handles display of validation status badge.
 * Individual messages are rendered inline in the spec sheet by renderSpecSheet().
 */

/**
 * Update validation status indicator.
 * Messages are rendered inline by renderSpecSheet() — this only updates the badge.
 * @param {boolean} valid - Whether the design is valid
 * @param {Array} messages - Validation messages (used for count display)
 */
export function updateValidationUI(valid, messages) {
    const statusDiv = document.getElementById('validation-status');

    const errorCount = messages.filter(m => m.severity === 'error').length;
    const warningCount = messages.filter(m => m.severity === 'warning').length;

    if (valid && warningCount === 0) {
        statusDiv.className = 'status-valid';
        statusDiv.textContent = '\u2713 Design valid';
    } else if (valid) {
        statusDiv.className = 'status-valid';
        statusDiv.textContent = `\u2713 Design valid \u2014 ${warningCount} warning${warningCount !== 1 ? 's' : ''}`;
    } else {
        statusDiv.className = 'status-error';
        statusDiv.textContent = `\u2717 ${errorCount} error${errorCount !== 1 ? 's' : ''}${warningCount > 0 ? `, ${warningCount} warning${warningCount !== 1 ? 's' : ''}` : ''}`;
    }
}
