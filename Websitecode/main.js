document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('suggestForm');
  const result = document.getElementById('result');

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    result.textContent = 'Working...';

    const payload = {
      calorie_goal: Number(document.getElementById('calorie').value) || 0,
      protein_goal: Number(document.getElementById('protein').value) || 0,
      vegan: document.getElementById('vegan').value === 'true',
      allergen: document.getElementById('allergen').value || ''
    };

    try {
      const resp = await fetch('/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok) {
        result.textContent = data.error || ('Server error: ' + resp.status);
        return;
      }
      if (data.success) {
        result.textContent = data.text;
      } else {
        result.textContent = data.error || 'No matching meal found.';
      }
    } catch (err) {
      result.textContent = 'Request failed: ' + err;
    }
  });
});