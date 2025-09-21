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
  const carbsInput = document.getElementById('carbs');
  const fatInput = document.getElementById('fat');
  const fiberInput = document.getElementById('fiber');
  const useRecommendedBtn = document.getElementById('useRecommended');
  const editGoalsBtn = document.getElementById('editGoals');
  const goalMessage = document.getElementById('goalMessage');
  const dailyTotals = document.getElementById('dailyTotals');
  const datasetButtons = document.querySelectorAll('.dataset-option');
  const datasetError = document.getElementById('datasetError');
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
      if (datasetError) {
        datasetError.textContent = '';
      }
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
    if (carbsInput) carbsInput.disabled = locked;
    if (fatInput) fatInput.disabled = locked;
    if (fiberInput) fiberInput.disabled = locked;
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
        const perMealCarbs = data.carb_goal || 0;
        const perMealFat = data.fat_goal || 0;
        const perMealFiber = data.fiber_goal || 0;
        const dailyCalories = data.daily_calorie_goal || perMealCalories;
        const dailyProtein = data.daily_protein_goal || perMealProtein;
        const dailyCarbs = data.daily_carb_goal || perMealCarbs;
        const dailyFat = data.daily_fat_goal || perMealFat;
        const dailyFiber = data.daily_fiber_goal || perMealFiber;
        const mealsPerDay = data.meals_per_day || 3;

        calorieInput.value = Math.round(perMealCalories);
        proteinInput.value = Math.round(perMealProtein);
        if (carbsInput) carbsInput.value = Math.round(perMealCarbs);
        if (fatInput) fatInput.value = Math.round(perMealFat);
        if (fiberInput) fiberInput.value = Math.round(perMealFiber);
        lockGoals(true);

        setGoalMessage(
          `Recommended target for this meal (assuming ${mealsPerDay} meals/day): ${Math.round(perMealCalories)} kcal, ${Math.round(perMealProtein)} g protein, ${Math.round(perMealCarbs)} g carbs, ${Math.round(perMealFat)} g fat, ${Math.round(perMealFiber)} g fiber (daily estimate: ${Math.round(dailyCalories)} kcal, ${Math.round(dailyProtein)} g protein, ${Math.round(dailyCarbs)} g carbs, ${Math.round(dailyFat)} g fat, ${Math.round(dailyFiber)} g fiber).`
        );
        setDailyTotals(`Daily requirement: ${Math.round(dailyCalories)} kcal, ${Math.round(dailyProtein)} g protein, ${Math.round(dailyCarbs)} g carbs, ${Math.round(dailyFat)} g fat, ${Math.round(dailyFiber)} g fiber.`);
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
    if (datasetError) {
      datasetError.textContent = '';
    }

    if (!selectedDatasetPath) {
      if (datasetError) {
        datasetError.textContent = 'Please select a dining court.';
      }
      return;
    }

    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    result.textContent = 'Working...';

    const isVegan = veganSelect.value === 'true';
    const excludedItems = (!isVegan && excludeSection)
      ? Array.from(excludeSection.querySelectorAll('input[type="checkbox"]:checked')).map((cb) => cb.value)
      : [];

    const payload = {
      calorie_goal: Number(calorieInput.value) || 0,
      protein_goal: Number(proteinInput.value) || 0,
      carb_goal: Number(carbsInput && carbsInput.value) || 0,
      fat_goal: Number(fatInput && fatInput.value) || 0,
      fiber_goal: Number(fiberInput && fiberInput.value) || 0,
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
