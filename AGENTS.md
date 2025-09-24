# Agent Guidelines for Laura Anthony Website

## Technology Stack
- **Hugo** static site generator (v0.131.0+)
- **Custom theme** located in `themes/laura-theme/`
- **TOML** configuration in `hugo.toml`
- **CSS** with custom properties for dark theme accessibility

## Build Commands
- `hugo server` - Start development server with hot reload
- `hugo` - Build static site to `public/` directory
- `hugo --minify` - Build minified production version
- `hugo version` - Check Hugo installation

## Code Style & Conventions
- **HTML**: Semantic markup with ARIA labels, accessibility-first design
- **CSS**: Use CSS custom properties (variables) defined in `:root`, BEM-like class naming
- **Content**: Markdown files in `content/` with YAML frontmatter
- **Images**: Store in `static/images/`, use `relURL` for Hugo paths
- **Colors**: Dark theme with green accents (#00cc66) and blue buttons (#2563eb), WCAG AA compliant
- **Typography**: Inter font family with enhanced readability spacing

## File Structure
- `content/` - Markdown content (blog, talks, quotes)
- `themes/laura-theme/` - Custom theme templates and assets
- `static/` - Static assets (images, etc.)
- `public/` - Generated site output (do not edit)
- `hugo.toml` - Site configuration

## Development Notes
- Accessibility is paramount - always include alt text, ARIA labels, semantic HTML
- Use Hugo's template functions: `relURL`, `safeHTML`, `.Site.Params`
- Test locally with `hugo server` before building
- No package.json - this is a pure Hugo site without Node.js dependencies