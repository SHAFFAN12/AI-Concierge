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
  iframe.src = "http://localhost:3000/widget";
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

    if (data.type === "autofill") {
      console.log("🧩 Autofill received:", data);
      const fields = data.payload?.fields || [];
      fields.forEach(({ selector, value }) => {
        const element = document.querySelector(selector);
        if (element) {
          element.value = value;
          element.dispatchEvent(new Event("input", { bubbles: true }));
          console.log(`✅ Filled ${selector} with "${value}"`);
        } else {
          console.warn(`⚠️ Element not found for selector: ${selector}`);
        }
      });

      // Optional: Auto-submit form if found
      const form = document.querySelector("form");
      if (form) {
        console.log("🚀 Form ready — auto-submitting...");
        form.dispatchEvent(new Event("submit", { bubbles: true }));
      }
    } else if (data.type === "click") {
      console.log("🖱️ Click action received:", data);
      const { element_text } = data.payload;
      if (element_text) {
        // Find the element by its text content using XPath
        const xpath = `//*[text()='${element_text}'] | //button[contains(.,'${element_text}')] | //a[contains(.,'${element_text}')]`;
        const element = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
        
        if (element) {
          element.click();
          console.log(`✅ Clicked on element with text: "${element_text}"`);
        } else {
          console.warn(`⚠️ Element not found with text: "${element_text}"`);
        }
      }
    }
  });
})();
