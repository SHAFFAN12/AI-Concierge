# How to Embed the AI Concierge Widget

To embed the AI Concierge widget on your website, add the following line of code to your HTML file, just before the closing `</body>` tag:

```html
<script src="http://localhost:3000/embed.js"></script>
```

This will add a "Chat" button to the bottom right corner of your page. Clicking this button will open the AI Concierge chat widget.

**Note:** For this to work, the frontend development server must be running (`npm run dev`). In a production environment, you would replace `http://localhost:3000` with the actual URL of your deployed frontend application.
