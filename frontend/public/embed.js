(function () {
  const widgetContainer = document.createElement("div");
  widgetContainer.id = "ai-concierge-widget";
  widgetContainer.style.position = "fixed";
  widgetContainer.style.bottom = "20px";
  widgetContainer.style.right = "20px";
  widgetContainer.style.zIndex = "9999";

  const button = document.createElement("button");
  button.id = "ai-concierge-button";
  button.innerText = "Chat";
  button.style.backgroundColor = "#007bff";
  button.style.color = "white";
  button.style.border = "none";
  button.style.padding = "10px 20px";
  button.style.borderRadius = "5px";
  button.style.cursor = "pointer";

  const iframe = document.createElement("iframe");
  iframe.id = "ai-concierge-iframe";
  // Determine base URL:
  // 1. data-base-url attribute on the embedding <script>
  // 2. origin of the script src
  // 3. fallback to current window origin
  const scriptEl = document.currentScript;
  let baseUrl = window.location.origin;
  if (scriptEl) {
    const attrBase = scriptEl.getAttribute("data-base-url");
    if (attrBase) {
      baseUrl = attrBase.replace(/\/$/, "");
    } else if (scriptEl.src) {
      try {
        baseUrl = new URL(scriptEl.src).origin;
      } catch (e) {
        // keep fallback
      }
    }
  }
  iframe.src = baseUrl;
  iframe.style.width = "400px";
  iframe.style.height = "600px";
  iframe.style.border = "1px solid #ccc";
  iframe.style.borderRadius = "10px";
  iframe.style.display = "none";
  iframe.style.marginTop = "10px";

  widgetContainer.appendChild(iframe);
  widgetContainer.appendChild(button);
  document.body.appendChild(widgetContainer);

  // Toggle chat window
  button.addEventListener("click", () => {
    const show = iframe.style.display === "none";
    iframe.style.display = show ? "block" : "none";
    button.innerText = show ? "Close" : "Chat";
  });

  // Send page info to iframe
  iframe.addEventListener("load", () => {
    setTimeout(() => {
      const currentUrl = window.location.href;
      const domain = window.location.hostname;
      console.log("🌐 Sending page info:", currentUrl);

      iframe.contentWindow.postMessage(
        {
          type: "page_info",
          payload: { url: currentUrl, domain },
        },
        "*"
      );
    }, 800);
  });

  // Listen for actions from the widget
  window.addEventListener("message", (event) => {
    const data = event.data;

    if (!data || !data.type) return;

    if (data.type === "action") {
      const { action, selector, value, x, y } = data.payload;
      console.log(`⚡ Action received: ${action}`, data.payload);

      try {
        if (action === "scroll") {
          if (selector) {
            const el = document.querySelector(selector);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
          } else if (value === "bottom") {
            window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
          } else if (value === "top") {
            window.scrollTo({ top: 0, behavior: "smooth" });
          } else if (typeof x === "number" || typeof y === "number") {
            window.scrollTo({ top: y || window.scrollY, left: x || window.scrollX, behavior: "smooth" });
          } else {
            // specific amount down
            window.scrollBy({ top: 500, behavior: "smooth" });
          }

        } else if (action === "click") {
          let el = null;
          if (selector) {
            el = document.querySelector(selector);
          } else if (value) {
            // Text search fallback
            const xpath = `//*[text()='${value}'] | //button[contains(.,'${value}')] | //a[contains(.,'${value}')]`;
            el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
          }

          if (el) {
            el.click();
            el.focus(); // Give focus
          } else {
            console.warn(`Element not found for click: ${selector || value}`);
          }

        } else if (action === "fill") {
          let el = document.querySelector(selector);

          // Fallback: Fuzzy search if selector failed
          if (!el) {
            const keyword = selector.replace(/[#.]/g, '').toLowerCase();
            if (!el) el = document.querySelector(`input[name*='${keyword}']`);
            if (!el) el = document.querySelector(`input[id*='${keyword}']`);
            if (!el) el = document.querySelector(`input[placeholder*='${keyword}' i]`);
            if (!el) {
              const xpath = `//label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${keyword}')]/following-sibling::input | //label[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${keyword}')]//input`;
              const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
              if (result) el = result.singleNodeValue;
            }
          }

          if (el) {
            el.focus(); // Focus first

            // React 15/16+ hack: react overrides the value setter, so we need to call the native one
            try {
              const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
              if (nativeInputValueSetter) {
                nativeInputValueSetter.call(el, value);
              } else {
                el.value = value;
              }
            } catch (e) {
              el.value = value;
            }

            el.dispatchEvent(new Event("input", { bubbles: true }));
            el.dispatchEvent(new Event("change", { bubbles: true }));
            el.dispatchEvent(new Event("blur", { bubbles: true })); // Blur to trigger validation
          } else {
            console.warn(`Element not found for fill: ${selector}`);
          }

        } else if (action === "navigate") {
          if (value) window.location.href = value;

        } else if (action === "hover") {
          const el = document.querySelector(selector);
          if (el) {
            el.dispatchEvent(new MouseEvent('mouseover', { view: window, bubbles: true, cancelable: true }));
            el.scrollIntoView({ behavior: "smooth", block: "nearest" });
          }
        }
      } catch (err) {
        console.error("Action failed:", err);
      }
    }

    // Keep legacy support if needed, or remove. keeping minimal legacy logic
    if (data.type === "autofill") {
      // ... existing autofill logic could be mapped to multiple "fill" actions, 
      // but for now we'll assume the agent uses the new "action" type.
    }
  });
})();
