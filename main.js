document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('suggestForm');
  const result = document.getElementById('result');
  const dataset = document.getElementById('dataset');
  const customPathLabel = document.getElementById('customPathLabel');
  const customPath = document.getElementById('customPath');

  dataset.addEventListener('change', () => {
    if (dataset.value === 'custom') {
      customPathLabel.style.display = '';
    } else {
      customPathLabel.style.display = 'none';
    }
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    result.textContent = 'Working...';

    // build payload including dataset selection and excluded meats
    const selectedDataset = dataset.value;
    let path = 'Windsor-20250922.xlsx';
    if (selectedDataset === 'hillenbrand') path = 'Hillenbrand-Lunch20250922.xlsx';
    if (selectedDataset === 'custom' && customPath.value.trim()) path = customPath.value.trim();

    const excluded = Array.from(document.querySelectorAll('input[name="exclude_meat"]:checked')).map(c => c.value);

    const payload = {
      path,
      calorie_goal: Number(document.getElementById('calorie').value) || 0,
      protein_goal: Number(document.getElementById('protein').value) || 0,
      vegan: document.getElementById('vegan').value === 'true',
      allergen: document.getElementById('allergen').value || '',
      excluded_meats: excluded
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