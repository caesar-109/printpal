PrintPal Design System - Modern Academic Print Management

Design Philosophy:
Create a minimal, sophisticated interface that prioritizes clarity and ease of use, drawing inspiration from Notion's typography, Vercel's space utilization, and Stripe's interactive elements.

Core Design Elements:

1. Typography:
- Primary: Inter (for UI elements and headings)
- Secondary: SF Pro Display or System UI (for body text)
- Monospace: SF Mono (for print request IDs and technical details)
- Font Scale: Follow a modular scale with 1.2 ratio
- Weights: Regular (400) for body, Medium (500) for UI, Semibold (600) for headings

2. Color Palette:
Primary Colors:
- Background: Subtle off-white (#FAFAFA) for light mode, Rich dark (#111111) for dark mode
- Text: Soft black (#18181B) for light mode, Off-white (#F4F4F5) for dark mode
- Primary Brand: Deep blue (#0F172A)

Accent Colors:
- Success: Sage green (#10B981)
- Warning: Warm amber (#F59E0B)
- Error: Soft red (#EF4444)
- Info: Cool blue (#3B82F6)

3. Components (using shadcn/ui):
- Cards: Floating effect with subtle shadows (box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04))
- Buttons: Pill-shaped with subtle hover transitions
- Tables: Borderless with hover states and subtle row separators
- Navigation: Clean, minimal top bar with contextual actions
- Status Indicators: Small pills with icons for print status

4. Spacing System:
- Base unit: 4px
- Content padding: 24px
- Section spacing: 32px
- Component gaps: 16px

5. Interface Elements:
- Icons: Use Lucide icons, 20px size, with consistent stroke width
- Dividers: Light gray (#E5E7EB), 1px width
- Tooltips: Dark background with white text for additional context
- Dropdowns: Clean, minimal with subtle transitions

6. Interaction States:
- Hover: Scale transforms (1.02) for clickable cards
- Active: Slight depression effect for buttons
- Focus: Subtle blue ring with offset
- Loading: Minimal spinner with brand color

7. Layout:
- Maximum content width: 1200px
- Sidebar width (if needed): 280px
- Card max-width: 400px for forms
- Responsive breakpoints following Tailwind defaults

8. Animation:
- Subtle transitions: 200ms ease-in-out
- Page transitions: Fade in/out (150ms)
- Success/error notifications: Slide and fade
- Loading states: Pulse animation

Special Features:
- Print status badges with dynamic colors and icons
- Smart tables with sticky headers
- Responsive grid for dashboard statistics
- Contextual help tooltips
- Progress indicators for multi-step processes

Accessibility:
- WCAG 2.1 AA compliant color contrast
- Clear focus indicators
- Semantic HTML structure
- Screen reader friendly status updates
- Keyboard navigation support

Mobile Considerations:
- Touch-friendly tap targets (minimum 44px)
- Simplified navigation for small screens
- Responsive typography scaling
- Collapsible sections for complex tables

This design system should create a professional, academic atmosphere while maintaining modern web aesthetics. The interface should feel light, responsive, and intuitive, making print management tasks effortless for both students and faculty.