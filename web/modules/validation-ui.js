/**
 * Validation UI Module
 *
 * Handles display of validation results and messages.
 */

/**
 * Update validation status and messages in the UI
 * @param {boolean} valid - Whether the design is valid
 * @param {Array} messages - Validation messages
 */
export function updateValidationUI(valid, messages) {
    const statusDiv = document.getElementById('validation-status');
    const messagesList = document.getElementById('validation-messages');

    // Update status indicator
    statusDiv.className = valid ? 'status-valid' : 'status-error';
    statusDiv.textContent = valid ? '✓ Design valid' : '✗ Design has errors';

    // Clear and populate messages list
    messagesList.innerHTML = '';
    messages.forEach(msg => {
        const li = document.createElement('li');
        li.className = `validation-${msg.severity}`;
        li.innerHTML = `<strong>${msg.code}</strong>: ${msg.message}`;
        if (msg.suggestion) {
            li.innerHTML += `<br><em>Suggestion: ${msg.suggestion}</em>`;
        }
        messagesList.appendChild(li);
    });
}
