# ELK Stack Lab Website

This directory contains the educational static website for the ELK Stack Ubuntu Jammy Build project.

## Structure

```
website/
├── index.html          # Main landing page
├── pages/              # Additional pages
│   ├── about.html
│   ├── components.html
│   ├── installation.html
│   └── tutorials.html
├── css/
│   └── style.css       # Custom styles
├── js/
│   └── main.js         # Interactive features
└── assets/
    └── images/         # Images and diagrams
```

## Features

- **Modern Design**: Built with Tailwind CSS for responsive, mobile-first design
- **Interactive**: Smooth scrolling, animations, and code copy functionality
- **Educational**: Comprehensive information about ELK Stack components
- **Accessible**: Semantic HTML and ARIA labels for accessibility

## Technologies

- HTML5
- Tailwind CSS (via CDN)
- Vanilla JavaScript
- Font Awesome icons
- Google Fonts (Inter)

## Local Development

Simply open `index.html` in a web browser. No build process required.

For a local server:

```bash
# Python 3
python3 -m http.server 8000

# Node.js (with http-server)
npx http-server -p 8000
```

Then visit `http://localhost:8000`

## Deployment

This is a static website and can be deployed to:
- GitHub Pages
- Netlify
- Vercel
- Any static hosting service

## License

Part of the ELK Stack Ubuntu Jammy Build project.
