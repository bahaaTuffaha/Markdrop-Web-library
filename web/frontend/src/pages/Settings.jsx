import { useEffect, useState } from "react";
import { api } from "../api.js";
import Topbar from "../components/Topbar.jsx";

const PROVIDERS = ["gemini", "openai", "anthropic", "groq", "openrouter", "litellm"];

const EMPTY = {
  convert_mode: "normal",
  add_tables: false,
  image_resolution_scale: 2,
  download_button_color: "#444444",
  enable_describe: false,
  ai_provider: "gemini",
  model: "",
  text_model: "",
  remove_images: false,
  remove_tables: false,
  image_descriptions: true,
  table_descriptions: true,
  max_retries: 3,
  retry_delay: 2,
  max_concurrency: 8,
  timeout_seconds: 120,
  image_prompt: "",
  table_prompt: "",
  max_concurrent_jobs: 1,
};

export default function Settings({ showToast }) {
  const [settings, setSettings] = useState(EMPTY);
  const [keys, setKeys] = useState({});
  const [engine, setEngine] = useState("full");
  const [providers, setProviders] = useState({});

  useEffect(() => {
    api
      .settings()
      .then((data) => {
        setSettings({ ...EMPTY, ...data.settings });
        setKeys(data.keys || {});
        setEngine(data.engine);
        setProviders(data.providers || {});
      })
      .catch((err) => showToast(err.message || "Could not load settings"));
  }, [showToast]);

  function update(name, value) {
    setSettings((current) => ({ ...current, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    const payloadKeys = {};
    for (const provider of PROVIDERS) {
      const value = keys[provider];
      if (value && !String(value).endsWith("****")) {
        payloadKeys[provider] = value;
      }
    }
    try {
      const saved = await api.saveSettings({ settings, keys: payloadKeys });
      setSettings({ ...EMPTY, ...saved.settings });
      setKeys(saved.keys || {});
      setEngine(saved.engine);
      setProviders(saved.providers || {});
      showToast("Settings saved");
    } catch (err) {
      showToast(err.message || "Could not save");
    }
  }

  return (
    <>
      <Topbar />
      <main className="page">
        <h1 className="page-title">Settings</h1>
        <p className="page-sub">Saved on the server. New drops use the snapshot taken at upload time.</p>
        <form className="form" onSubmit={onSubmit}>
          <section className="card">
            <h2>Convert</h2>
            {engine === "lite" ? (
              <p className="disabled-note">
                This image was built with MARKDROP_ENGINE=lite. Normal (Docling) convert is unavailable
                — rebuild with ENGINE=full to enable it.
              </p>
            ) : null}
            <label>
              Mode
              <select
                value={settings.convert_mode}
                onChange={(event) => update("convert_mode", event.target.value)}
              >
                <option value="normal" disabled={engine === "lite"}>
                  Normal (Docling) — default
                </option>
                <option value="fast">Fast (PyMuPDF only)</option>
              </select>
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.add_tables}
                onChange={(event) => update("add_tables", event.target.checked)}
              />
              Add downloadable Excel tables to HTML
            </label>
            <label>
              Image resolution scale
              <input
                type="number"
                min="0.5"
                max="8"
                step="0.1"
                value={settings.image_resolution_scale}
                onChange={(event) => update("image_resolution_scale", Number(event.target.value))}
              />
            </label>
            <label>
              Download button color
              <input
                type="text"
                value={settings.download_button_color}
                onChange={(event) => update("download_button_color", event.target.value)}
              />
            </label>
          </section>

          <section className="card">
            <h2>Describe (optional)</h2>
            <p className="hint">Off by default. When enabled, runs after convert using the selected provider.</p>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.enable_describe}
                onChange={(event) => update("enable_describe", event.target.checked)}
              />
              Generate AI descriptions after convert
            </label>
            <label>
              Provider
              <select
                value={settings.ai_provider}
                onChange={(event) => update("ai_provider", event.target.value)}
              >
                {PROVIDERS.map((provider) => (
                  <option
                    key={provider}
                    value={provider}
                    disabled={providers[provider] && !providers[provider].available}
                  >
                    {provider}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Vision model override
              <input
                type="text"
                value={settings.model}
                placeholder="leave empty for provider default"
                onChange={(event) => update("model", event.target.value)}
              />
            </label>
            <label>
              Text model override
              <input
                type="text"
                value={settings.text_model}
                placeholder="leave empty for provider default"
                onChange={(event) => update("text_model", event.target.value)}
              />
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.image_descriptions}
                onChange={(event) => update("image_descriptions", event.target.checked)}
              />
              Image descriptions
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.table_descriptions}
                onChange={(event) => update("table_descriptions", event.target.checked)}
              />
              Table descriptions
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.remove_images}
                onChange={(event) => update("remove_images", event.target.checked)}
              />
              Replace images with descriptions
            </label>
            <label className="check">
              <input
                type="checkbox"
                checked={!!settings.remove_tables}
                onChange={(event) => update("remove_tables", event.target.checked)}
              />
              Replace tables with summaries
            </label>
            <label>
              Max retries
              <input
                type="number"
                value={settings.max_retries}
                onChange={(event) => update("max_retries", Number(event.target.value))}
              />
            </label>
            <label>
              Retry delay (seconds)
              <input
                type="number"
                value={settings.retry_delay}
                onChange={(event) => update("retry_delay", Number(event.target.value))}
              />
            </label>
            <label>
              Max concurrency
              <input
                type="number"
                value={settings.max_concurrency}
                onChange={(event) => update("max_concurrency", Number(event.target.value))}
              />
            </label>
            <label>
              Timeout (seconds)
              <input
                type="number"
                value={settings.timeout_seconds}
                onChange={(event) => update("timeout_seconds", Number(event.target.value))}
              />
            </label>
            <label>
              Image prompt
              <textarea
                value={settings.image_prompt}
                onChange={(event) => update("image_prompt", event.target.value)}
              />
            </label>
            <label>
              Table prompt
              <textarea
                value={settings.table_prompt}
                onChange={(event) => update("table_prompt", event.target.value)}
              />
            </label>
          </section>

          <section className="card">
            <h2>API keys</h2>
            <p className="hint">
              Stored in the data volume as .env (mode 0600). Leave a field unchanged to keep the saved
              key. Paste a new key to replace it.
            </p>
            {PROVIDERS.map((provider) => (
              <label key={provider}>
                {provider}
                <input
                  type="password"
                  autoComplete="off"
                  value={keys[provider] || ""}
                  placeholder={keys[provider] ? "saved" : ""}
                  onChange={(event) =>
                    setKeys((current) => ({ ...current, [provider]: event.target.value }))
                  }
                />
              </label>
            ))}
          </section>

          <section className="card">
            <h2>Server</h2>
            <label>
              Max concurrent conversions
              <input
                type="number"
                min="1"
                max="4"
                value={settings.max_concurrent_jobs}
                onChange={(event) => update("max_concurrent_jobs", Number(event.target.value))}
              />
            </label>
            <p className="hint">Keep this at 1 unless the host has plenty of RAM. Jobs beyond the limit stay queued.</p>
          </section>

          <div className="actions-row">
            <button className="btn" type="submit">
              Save settings
            </button>
          </div>
        </form>
      </main>
    </>
  );
}
