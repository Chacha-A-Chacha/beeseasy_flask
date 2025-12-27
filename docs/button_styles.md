# Button Styles Guide

Standard button styles for use across templates.

---

## Light Background Buttons

Use these on white or light gray backgrounds (bg-white, bg-gray-50, etc.)

### Primary Button (Light Background)
```html
<a href="#" class="rounded-full bg-accent-orange px-6 py-3 text-base font-semibold text-white shadow-lg hover:bg-accent-yellow hover:text-primary-dark transition-all duration-300">
    Register Now
</a>
```

### Secondary Button (Light Background)
```html
<a href="#" class="rounded-full bg-transparent border-2 border-primary-dark text-primary-dark px-6 py-3 text-base font-semibold hover:bg-primary-dark hover:text-white transition-all duration-300">
    View Full Agenda
</a>
```

---

## Dark Background Buttons

Use these on dark backgrounds (bg-primary-dark, bg-primary-medium, bg-gray-900, etc.)

### Primary Button (Dark Background)
```html
<a href="#" class="rounded-full bg-accent-orange px-6 py-3 text-base font-semibold text-white shadow-lg hover:bg-accent-yellow hover:text-primary-dark transition-all duration-300">
    Register Now
</a>
```

### Secondary Button (Dark Background)
```html
<a href="#" class="rounded-full bg-transparent border-2 border-accent-yellow text-accent-yellow px-6 py-3 text-base font-semibold hover:bg-accent-yellow hover:text-primary-dark transition-all duration-300">
    View Full Agenda
</a>
```

---

## Notes

- Primary buttons are identical for both backgrounds
- Secondary buttons differ in border and text color:
  - Light background: `border-primary-dark text-primary-dark`
  - Dark background: `border-accent-yellow text-accent-yellow`
- All buttons use `rounded-full` for pill shape
- All buttons include `transition-all duration-300` for smooth hover effects
