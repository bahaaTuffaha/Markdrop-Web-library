const PROVIDERS = ["gemini", "openai", "anthropic", "groq", "openrouter", "litellm"];

function fill(form, settings, keys, meta) {
  const engine = meta.engine;
  form.convert_mode.value = settings.convert_mode;
  form.convert_mode.querySelector('option[value="normal"]').disabled = engine === "lite";
  document.getElementById("engine-note").hidden = engine !== "lite";
  form.add_tables.checked = !!settings.add_tables;
  form.image_resolution_scale.value = settings.image_resolution_scale;
  form.download_button_color.value = settings.download_button_color;
  form.enable_describe.checked = !!settings.enable_describe;
  form.ai_provider.value = settings.ai_provider;
  form.model.value = settings.model || "";
  form.text_model.value = settings.text_model || "";
  form.remove_images.checked = !!settings.remove_images;
  form.remove_tables.checked = !!settings.remove_tables;
  form.image_descriptions.checked = !!settings.image_descriptions;
  form.table_descriptions.checked = !!settings.table_descriptions;
  form.max_retries.value = settings.max_retries;
  form.retry_delay.value = settings.retry_delay;
  form.max_concurrency.value = settings.max_concurrency;
  form.timeout_seconds.value = settings.timeout_seconds;
  form.image_prompt.value = settings.image_prompt || "";
  form.table_prompt.value = settings.table_prompt || "";
  form.max_concurrent_jobs.value = settings.max_concurrent_jobs;
  for (const provider of PROVIDERS) {
    const input = form.querySelector(`[name="key_${provider}"]`);
    if (input) {
      input.value = keys[provider] || "";
      input.placeholder = keys[provider] ? "saved" : "";
    }
    const option = form.ai_provider.querySelector(`option[value="${provider}"]`);
    if (option && meta.providers && meta.providers[provider]) {
      option.disabled = !meta.providers[provider].available;
    }
  }
}

async function load() {
  const data = await api.settings();
  fill(document.getElementById("settings-form"), data.settings, data.keys, data);
}

document.getElementById("settings-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const settings = {
    convert_mode: form.convert_mode.value,
    add_tables: form.add_tables.checked,
    image_resolution_scale: Number(form.image_resolution_scale.value),
    download_button_color: form.download_button_color.value,
    enable_describe: form.enable_describe.checked,
    ai_provider: form.ai_provider.value,
    model: form.model.value,
    text_model: form.text_model.value,
    remove_images: form.remove_images.checked,
    remove_tables: form.remove_tables.checked,
    image_descriptions: form.image_descriptions.checked,
    table_descriptions: form.table_descriptions.checked,
    max_retries: Number(form.max_retries.value),
    retry_delay: Number(form.retry_delay.value),
    max_concurrency: Number(form.max_concurrency.value),
    timeout_seconds: Number(form.timeout_seconds.value),
    image_prompt: form.image_prompt.value,
    table_prompt: form.table_prompt.value,
    max_concurrent_jobs: Number(form.max_concurrent_jobs.value),
  };
  const keys = {};
  for (const provider of PROVIDERS) {
    const value = form.querySelector(`[name="key_${provider}"]`).value;
    if (value && !value.endsWith("****")) {
      keys[provider] = value;
    }
  }
  try {
    const saved = await api.saveSettings({ settings, keys });
    fill(form, saved.settings, saved.keys, saved);
    toast("Settings saved");
  } catch (err) {
    toast(err.message || "Could not save");
  }
});

load().catch((err) => toast(err.message || "Could not load settings"));
