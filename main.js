document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('suggestForm');
  const result = document.getElementById('result');
  const veganSelect = document.getElementById('vegan');
  const excludeSection = document.getElementById('excludeSection');
  const ageInput = document.getElementById('age');
  const genderSelect = document.getElementById('gender');
  const heightInput = document.getElementById('height');
  const weightInput = document.getElementById('weight');
  const activitySelect = document.getElementById('activity');
  const calorieInput = document.getElementById('calorie');
  const proteinInput = document.getElementById('protein');
  const useRecommendedBtn = document.getElementById('useRecommended');
  const editGoalsBtn = document.getElementById('editGoals');
  const goalMessage = document.getElementById('goalMessage');
  const dailyTotals = document.getElementById('dailyTotals');
  const datasetButtons = document.querySelectorAll('.dataset-option');
  let goalsLocked = false;
  let selectedDatasetPath = (() => {
    if (!datasetButtons || datasetButtons.length === 0) {
      return 'Windsor-20250922.xlsx';
    }
    const preset = Array.from(datasetButtons).find((btn) => btn.classList.contains('active'));
    return (preset && preset.dataset.path) || datasetButtons[0].dataset.path;
  })();

  datasetButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      selectedDatasetPath = btn.dataset.path;
      datasetButtons.forEach((other) => {
        other.classList.toggle('active', other === btn);
      });
    });
  });

  const toggleExcludeSection = () => {
    if (!excludeSection) return;
    const isVegan = veganSelect.value === 'true';
    excludeSection.classList.toggle('visible', !isVegan);
  };

  veganSelect.addEventListener('change', toggleExcludeSection);
  toggleExcludeSection();

  const lockGoals = (locked) => {
    goalsLocked = locked;
    calorieInput.disabled = locked;
    proteinInput.disabled = locked;
    if (editGoalsBtn) editGoalsBtn.disabled = !locked;
  };

  const setGoalMessage = (msg, isError = false) => {
    if (!goalMessage) return;
    goalMessage.textContent = msg || '';
    goalMessage.classList.toggle('error', !!isError);
  };

  const setDailyTotals = (msg) => {
    if (!dailyTotals) return;
    dailyTotals.textContent = msg || '';
  };

  lockGoals(false);
  setGoalMessage('');
  setDailyTotals('');

  const prerequisiteInputs = [ageInput, heightInput, weightInput, genderSelect, activitySelect];

  const handlePrereqChange = () => {
    if (goalsLocked) {
      lockGoals(false);
      setGoalMessage('Inputs changed. Click "Use recommended goals" to refresh.');
      setDailyTotals('');
    }
  };

  prerequisiteInputs.forEach((el) => {
    if (!el) return;
    el.addEventListener('input', handlePrereqChange);
    el.addEventListener('change', handlePrereqChange);
  });

  if (useRecommendedBtn) {
    useRecommendedBtn.addEventListener('click', async () => {
      const age = Number(ageInput.value);
      const height = Number(heightInput.value);
      const weight = Number(weightInput.value);
      const gender = (genderSelect && genderSelect.value) || 'unspecified';
      const activity = (activitySelect && activitySelect.value) || 'sedentary';

      if (!age || !height || !weight) {
        setGoalMessage('Please provide age, height, and weight to get recommendations.', true);
        return;
      }

      useRecommendedBtn.disabled = true;
      try {
        setGoalMessage('Calculating recommended goals...');
        setDailyTotals('');
        const resp = await fetch('/recommend', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            age,
            height_cm: height,
            weight_kg: weight,
            gender,
            activity_level: activity
          })
        });
        const data = await resp.json();
        if (!resp.ok || !data.success) {
          const message = data.error || `Unable to calculate recommendations (status ${resp.status}).`;
          setGoalMessage(message, true);
          setDailyTotals('');
          return;
        }

        const perMealCalories = data.calorie_goal || 0;
        const perMealProtein = data.protein_goal || 0;
        const dailyCalories = data.daily_calorie_goal || perMealCalories;
        const dailyProtein = data.daily_protein_goal || perMealProtein;
        const mealsPerDay = data.meals_per_day || 3;

        calorieInput.value = Math.round(perMealCalories);
        proteinInput.value = Math.round(perMealProtein);
        lockGoals(true);

        setGoalMessage(
          `Recommended target for this meal (assuming ${mealsPerDay} meals/day): ${Math.round(perMealCalories)} kcal & ${Math.round(perMealProtein)} g protein (daily estimate: ${Math.round(dailyCalories)} kcal, ${Math.round(dailyProtein)} g).`
        );
        setDailyTotals(`Daily requirement: ${Math.round(dailyCalories)} kcal & ${Math.round(dailyProtein)} g protein.`);
      } catch (err) {
        setGoalMessage(`Failed to fetch recommendations: ${err}`, true);
        setDailyTotals('');
      } finally {
        useRecommendedBtn.disabled = false;
      }
    });
  }

  if (editGoalsBtn) {
    editGoalsBtn.addEventListener('click', () => {
      lockGoals(false);
      setGoalMessage('You can now edit the calorie and protein goals.');
      setDailyTotals('');
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    result.textContent = 'Working...';

    const isVegan = veganSelect.value === 'true';
    const excludedItems = (!isVegan && excludeSection)
      ? Array.from(excludeSection.querySelectorAll('input[type="checkbox"]:checked')).map((cb) => cb.value)
      : [];

    const payload = {
      calorie_goal: Number(calorieInput.value) || 0,
      protein_goal: Number(proteinInput.value) || 0,
      vegan: isVegan,
      excluded_items: excludedItems,
      path: selectedDatasetPath
    };

    try {
      const resp = await fetch('/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (!resp.ok) {
        result.textContent = data.error || (`Server error: ${resp.status}`);
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
