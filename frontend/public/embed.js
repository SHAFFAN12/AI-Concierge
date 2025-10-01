(function() {
  // Create a container for the widget
  const widgetContainer = document.createElement('div');
  widgetContainer.id = 'ai-concierge-widget';
  widgetContainer.style.position = 'fixed';
  widgetContainer.style.bottom = '20px';
  widgetContainer.style.right = '20px';
  widgetContainer.style.zIndex = '9999';

  // Create the button
  const button = document.createElement('button');
  button.id = 'ai-concierge-button';
  button.innerText = 'Chat';
  button.style.backgroundColor = '#007bff';
  button.style.color = 'white';
  button.style.border = 'none';
  button.style.padding = '10px 20px';
  button.style.borderRadius = '5px';
  button.style.cursor = 'pointer';

  // Create the iframe
  const iframe = document.createElement('iframe');
  iframe.id = 'ai-concierge-iframe';
  iframe.src = 'http://localhost:3000/widget';
  iframe.style.width = '400px';
  iframe.style.height = '600px';
  iframe.style.border = '1px solid #ccc';
  iframe.style.borderRadius = '10px';
  iframe.style.display = 'none'; // Hidden by default
  iframe.style.marginTop = '10px';

  // Append elements to the container
  widgetContainer.appendChild(iframe);
  widgetContainer.appendChild(button);

  // Append the container to the body
  document.body.appendChild(widgetContainer);

  // Add event listener to the button
  button.addEventListener('click', () => {
    if (iframe.style.display === 'none') {
      iframe.style.display = 'block';
      button.innerText = 'Close';
    } else {
      iframe.style.display = 'none';
      button.innerText = 'Chat';
    }
  });

  // Listen for messages from the iframe
  window.addEventListener('message', (event) => {
    // IMPORTANT: Check the origin of the event for security
    if (event.origin !== 'http://localhost:3000') {
      return;
    }

    const data = event.data;

    if (data.type === 'autofill') {
      const { selector, value } = data.payload;
      const element = document.querySelector(selector);
      if (element) {
        element.value = value;
      }
    }
  });
})();
