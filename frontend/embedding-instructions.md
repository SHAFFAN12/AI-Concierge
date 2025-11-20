# AI Concierge Widget Embedding Instructions

To embed the AI Concierge widget into any external website, you can use an `<iframe>` tag.

## Widget URL

Once your Next.js application is deployed, the widget will be accessible at a URL similar to this (replace `your-domain.com` with your actual domain):

`https://your-domain.com/widget/embed`

During local development, you can access it at:

`http://localhost:3000/widget/embed`

## Embedding Code

Copy and paste the following HTML snippet into the `<body>` section of your external website's HTML where you want the widget to appear:

```html
<iframe
  src="https://your-domain.com/widget/embed"
  width="350px"  <!-- Suggested width -->
  height="500px" <!-- Suggested height -->
  frameborder="0"
  scrolling="no"
  style="border: none; position: fixed; bottom: 20px; right: 20px; z-index: 1000;"
  title="AI Concierge Chat Widget"
></iframe>
```

### Explanation of Attributes:

*   `src`: This **must** be the URL of your deployed AI Concierge widget page.
*   `width`: Sets the width of the widget. You can adjust this as needed.
*   `height`: Sets the height of the widget. You can adjust this as needed.
*   `frameborder="0"`: Removes the default iframe border.
*   `scrolling="no"`: Prevents unnecessary scrollbars within the iframe (the chat content itself has internal scrolling).
*   `style`:
    *   `border: none;`: Ensures no visual border is present.
    *   `position: fixed; bottom: 20px; right: 20px;`: Positions the widget fixed to the bottom-right corner of the screen. Adjust `bottom` and `right` values as per your design.
    *   `z-index: 1000;`: Ensures the widget appears above most other content on the page.
*   `title`: Provides an accessible title for the iframe.

## Customization (Advanced)

Currently, direct customization via URL parameters is not implemented but can be added. In the future, you could pass parameters like this:

```html
<iframe src="https://your-domain.com/widget/embed?theme=dark&initialMessage=Hello!" ...></iframe>
```

And then, within the `EmbedWidgetPage` component, you would read these URL parameters using Next.js's router and apply the customizations.