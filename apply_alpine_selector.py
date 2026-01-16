#!/usr/bin/env python3
"""
Script to apply Alpine.js country selector to attendee.html
Replaces the old intl-tel-input dependent country selector with Alpine.js implementation
"""

import os
import sys

# HTML replacement for country field (lines ~475-488)
HTML_REPLACEMENT = """                                <!-- Country Selector with Alpine.js -->
                                <div x-data="countrySelector()" x-init="init()">
                                    {{ form.country.label(class="block text-sm font-medium text-primary-dark mb-1") }}

                                    <!-- Custom Searchable Dropdown -->
                                    <div class="relative">
                                        <!-- Display Input -->
                                        <div class="relative">
                                            <input
                                                type="text"
                                                x-model="search"
                                                @click="open = true"
                                                @keydown.escape="open = false"
                                                @keydown.arrow-down.prevent="focusNext()"
                                                @keydown.arrow-up.prevent="focusPrevious()"
                                                @keydown.enter.prevent="selectFocused()"
                                                placeholder="Search or select your country"
                                                class="w-full px-3.5 py-2 border border-gray-300 rounded-md focus:ring-accent-yellow focus:border-accent-yellow"
                                                autocomplete="off"
                                            />
                                            <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
                                                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                                                </svg>
                                            </div>
                                        </div>

                                        <!-- Dropdown List -->
                                        <div
                                            x-show="open && filteredCountries.length > 0"
                                            @click.outside="open = false"
                                            x-transition:enter="transition ease-out duration-100"
                                            x-transition:enter-start="transform opacity-0 scale-95"
                                            x-transition:enter-end="transform opacity-100 scale-100"
                                            x-transition:leave="transition ease-in duration-75"
                                            x-transition:leave-start="transform opacity-100 scale-100"
                                            x-transition:leave-end="transform opacity-0 scale-95"
                                            class="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-60 overflow-auto"
                                            style="display: none;"
                                        >
                                            <template x-for="(country, index) in filteredCountries" :key="country">
                                                <div
                                                    @click="selectCountry(country)"
                                                    @mouseenter="focusedIndex = index"
                                                    :class="{
                                                        'bg-accent-yellow text-primary-dark': focusedIndex === index,
                                                        'hover:bg-gray-100': focusedIndex !== index
                                                    }"
                                                    class="px-3.5 py-2 cursor-pointer transition-colors"
                                                    x-text="country"
                                                ></div>
                                            </template>
                                        </div>

                                        <!-- No results message -->
                                        <div
                                            x-show="open && search && filteredCountries.length === 0"
                                            class="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg p-3"
                                            style="display: none;"
                                        >
                                            <p class="text-sm text-gray-500">No countries found matching "<span x-text="search"></span>"</p>
                                        </div>
                                    </div>

                                    <!-- Hidden select field (actual form field) -->
                                    {{ form.country(style="display: none;", **{"x-ref": "hiddenSelect"}) }}

                                    <!-- Error display -->
                                    {% if form.country.errors %}
                                    <p class="text-red-600 text-xs mt-1">
                                        {{ form.country.errors[0] }}
                                    </p>
                                    {% endif %}
                                </div>"""

# JavaScript replacement for scripts section
JS_REPLACEMENT = """<script>
    /**
     * Alpine.js Country Selector Component
     */
    function countrySelector() {
        return {
            // Component state
            open: false,
            search: '',
            selectedCountry: '',
            focusedIndex: 0,

            // Comprehensive country list (195 countries)
            countries: [
                'Afghanistan', 'Albania', 'Algeria', 'Andorra', 'Angola',
                'Antigua and Barbuda', 'Argentina', 'Armenia', 'Australia', 'Austria',
                'Azerbaijan', 'Bahamas', 'Bahrain', 'Bangladesh', 'Barbados',
                'Belarus', 'Belgium', 'Belize', 'Benin', 'Bhutan',
                'Bolivia', 'Bosnia and Herzegovina', 'Botswana', 'Brazil', 'Brunei',
                'Bulgaria', 'Burkina Faso', 'Burundi', 'Cabo Verde', 'Cambodia',
                'Cameroon', 'Canada', 'Central African Republic', 'Chad', 'Chile',
                'China', 'Colombia', 'Comoros', 'Congo', 'Costa Rica',
                'Croatia', 'Cuba', 'Cyprus', 'Czech Republic', 'Denmark',
                'Djibouti', 'Dominica', 'Dominican Republic', 'DR Congo', 'Ecuador',
                'Egypt', 'El Salvador', 'Equatorial Guinea', 'Eritrea', 'Estonia',
                'Eswatini', 'Ethiopia', 'Fiji', 'Finland', 'France',
                'Gabon', 'Gambia', 'Georgia', 'Germany', 'Ghana',
                'Greece', 'Grenada', 'Guatemala', 'Guinea', 'Guinea-Bissau',
                'Guyana', 'Haiti', 'Honduras', 'Hungary', 'Iceland',
                'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland',
                'Israel', 'Italy', 'Ivory Coast', 'Jamaica', 'Japan',
                'Jordan', 'Kazakhstan', 'Kenya', 'Kiribati', 'Kosovo',
                'Kuwait', 'Kyrgyzstan', 'Laos', 'Latvia', 'Lebanon',
                'Lesotho', 'Liberia', 'Libya', 'Liechtenstein', 'Lithuania',
                'Luxembourg', 'Madagascar', 'Malawi', 'Malaysia', 'Maldives',
                'Mali', 'Malta', 'Marshall Islands', 'Mauritania', 'Mauritius',
                'Mexico', 'Micronesia', 'Moldova', 'Monaco', 'Mongolia',
                'Montenegro', 'Morocco', 'Mozambique', 'Myanmar', 'Namibia',
                'Nauru', 'Nepal', 'Netherlands', 'New Zealand', 'Nicaragua',
                'Niger', 'Nigeria', 'North Korea', 'North Macedonia', 'Norway',
                'Oman', 'Pakistan', 'Palau', 'Palestine', 'Panama',
                'Papua New Guinea', 'Paraguay', 'Peru', 'Philippines', 'Poland',
                'Portugal', 'Qatar', 'Romania', 'Russia', 'Rwanda',
                'Saint Kitts and Nevis', 'Saint Lucia', 'Saint Vincent and the Grenadines',
                'Samoa', 'San Marino', 'Sao Tome and Principe', 'Saudi Arabia',
                'Senegal', 'Serbia', 'Seychelles', 'Sierra Leone', 'Singapore',
                'Slovakia', 'Slovenia', 'Solomon Islands', 'Somalia', 'South Africa',
                'South Korea', 'South Sudan', 'Spain', 'Sri Lanka', 'Sudan',
                'Suriname', 'Sweden', 'Switzerland', 'Syria', 'Taiwan',
                'Tajikistan', 'Tanzania', 'Thailand', 'Timor-Leste', 'Togo',
                'Tonga', 'Trinidad and Tobago', 'Tunisia', 'Turkey', 'Turkmenistan',
                'Tuvalu', 'Uganda', 'Ukraine', 'United Arab Emirates', 'United Kingdom',
                'United States', 'Uruguay', 'Uzbekistan', 'Vanuatu', 'Vatican City',
                'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe'
            ],

            // Computed property: Filtered countries based on search
            get filteredCountries() {
                if (!this.search) {
                    return this.countries;
                }
                const searchLower = this.search.toLowerCase();
                return this.countries.filter(country =>
                    country.toLowerCase().includes(searchLower)
                );
            },

            // Initialize component
            init() {
                // Check if there's a pre-selected value (e.g., form validation error)
                const hiddenSelect = this.$refs.hiddenSelect;
                if (hiddenSelect && hiddenSelect.value) {
                    this.selectedCountry = hiddenSelect.value;
                    this.search = hiddenSelect.value;
                }

                // Set up phone input listener for auto-selection
                this.setupPhoneInputListener();

                // Watch for changes to sync with hidden select
                this.$watch('selectedCountry', (value) => {
                    if (this.$refs.hiddenSelect) {
                        this.$refs.hiddenSelect.value = value;
                    }
                });
            },

            // Select a country
            selectCountry(country) {
                this.selectedCountry = country;
                this.search = country;
                this.open = false;
                this.focusedIndex = 0;

                // Update hidden select field
                if (this.$refs.hiddenSelect) {
                    this.$refs.hiddenSelect.value = country;

                    // Trigger change event for any listeners
                    const event = new Event('change', { bubbles: true });
                    this.$refs.hiddenSelect.dispatchEvent(event);
                }
            },

            // Keyboard navigation: Focus next item
            focusNext() {
                if (!this.open) {
                    this.open = true;
                    return;
                }
                this.focusedIndex = Math.min(
                    this.focusedIndex + 1,
                    this.filteredCountries.length - 1
                );
            },

            // Keyboard navigation: Focus previous item
            focusPrevious() {
                if (!this.open) {
                    this.open = true;
                    return;
                }
                this.focusedIndex = Math.max(this.focusedIndex - 1, 0);
            },

            // Keyboard navigation: Select focused item
            selectFocused() {
                if (this.open && this.filteredCountries[this.focusedIndex]) {
                    this.selectCountry(this.filteredCountries[this.focusedIndex]);
                }
            },

            // Auto-select country based on phone input
            setupPhoneInputListener() {
                const phoneInput = document.getElementById('phone_international');
                if (!phoneInput) return;

                // Listen for country change from intl-tel-input
                phoneInput.addEventListener('countrychange', () => {
                    if (!window.intlTelInputGlobals) return;

                    const iti = window.intlTelInputGlobals.getInstance(phoneInput);
                    if (!iti) return;

                    const countryData = iti.getSelectedCountryData();
                    if (!countryData || !countryData.name) return;

                    // Map intl-tel-input country name to our list
                    const countryName = this.mapPhoneCountryToList(countryData.name);

                    if (countryName && this.countries.includes(countryName)) {
                        this.selectCountry(countryName);
                    }
                });
            },

            // Map phone input country names to our country list
            mapPhoneCountryToList(phoneCountry) {
                // Direct match
                if (this.countries.includes(phoneCountry)) {
                    return phoneCountry;
                }

                // Common variations/aliases
                const countryMap = {
                    'United States of America': 'United States',
                    'USA': 'United States',
                    'UK': 'United Kingdom',
                    'Great Britain': 'United Kingdom',
                    'UAE': 'United Arab Emirates',
                    'DRC': 'DR Congo',
                    'Democratic Republic of the Congo': 'DR Congo',
                    'Republic of the Congo': 'Congo',
                    'South Korea (Republic of Korea)': 'South Korea',
                    'North Korea (Democratic People\'s Republic of Korea)': 'North Korea',
                    'The Netherlands': 'Netherlands',
                    'The Bahamas': 'Bahamas',
                    'The Gambia': 'Gambia',
                    'Republic of Ireland': 'Ireland',
                    'People\'s Republic of China': 'China',
                    'Russian Federation': 'Russia',
                    'Republic of China (Taiwan)': 'Taiwan'
                };

                return countryMap[phoneCountry] || phoneCountry;
            }
        };
    }
</script>"""


def apply_changes():
    """Apply Alpine.js country selector changes to attendee.html"""

    file_path = "app/templates/register/attendee.html"

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found!")
        return False

    # Read the file
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Create backup
    backup_path = file_path + ".backup2"
    with open(backup_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created backup: {backup_path}")

    # Split into lines for easier manipulation
    lines = content.split("\n")

    # Find and replace HTML section (country field)
    # Looking for the old country field pattern
    new_lines = []
    i = 0
    html_replaced = False

    while i < len(lines):
        line = lines[i]

        # Find the start of country field div
        if (
            not html_replaced
            and '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">' in line
            and i > 460
        ):
            # Add the grid div
            new_lines.append(line)
            i += 1

            # Check if next line is the old country div
            if i < len(lines) and "<div>" in lines[i]:
                # Skip old country field (lines until the closing </div> of country field)
                new_lines.append(HTML_REPLACEMENT)

                # Skip lines until we find the city field div
                depth = 1
                i += 1
                while i < len(lines) and depth > 0:
                    if "<div>" in lines[i] or "<div " in lines[i]:
                        depth += 1
                    if "</div>" in lines[i]:
                        depth -= 1
                    i += 1

                html_replaced = True
                print("✓ Replaced HTML section (country field)")
                continue

        new_lines.append(line)
        i += 1

    # Join back and find/replace JavaScript section
    content = "\n".join(new_lines)

    # Find and replace the old script
    script_start = content.find("{% endblock %} {% block scripts %}")
    script_end = content.find("{% endblock %}", script_start + 35)

    if script_start != -1 and script_end != -1:
        # Find the actual script content between the markers
        old_script_start = content.find("<script>", script_start)
        old_script_end = content.find("</script>", old_script_start)

        if old_script_start != -1 and old_script_end != -1:
            # Replace the script content
            before = content[:old_script_start]
            after = content[old_script_end + 9 :]  # 9 = len('</script>')

            content = before + JS_REPLACEMENT + after
            print("✓ Replaced JavaScript section")
        else:
            print("⚠ Warning: Could not find script tags")
    else:
        print("⚠ Warning: Could not find {% block scripts %}")

    # Write the modified content
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✓ Successfully applied Alpine.js country selector to {file_path}")
    print(f"✓ Backup saved as {backup_path}")
    print("\nChanges applied:")
    print("  1. Country field now uses Alpine.js searchable dropdown")
    print("  2. Removed dependency on intl-tel-input for country data")
    print("  3. Added keyboard navigation support")
    print("  4. Auto-selection from phone input still works")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Alpine.js Country Selector Implementation Script")
    print("=" * 60)
    print()

    success = apply_changes()

    if success:
        print("\n✓ Done! Test the registration form to verify.")
        sys.exit(0)
    else:
        print("\n✗ Failed to apply changes.")
        sys.exit(1)
