"""Jinja filters for roles/app_config/tasks/bazarr.yml.

`bazarr_settings_form`: the Bazarr settings that differ, as form fields. Bazarr's settings
API returns JSON grouped by section but only accepts form fields named
"settings-<section>-<key>", with booleans as "true"/"false" and lists as repeated fields.

    {{ wanted | bazarr_settings_form(current) }}

`wanted` and `current` are {section: {key: value}}; the result holds only the values in
`wanted` that differ from `current`, so an empty result means nothing to change.

`bazarr_language_profile`: a language profile as Bazarr stores it, one item per language
with the defaults of Bazarr's profile editor (normal subtitles, not forced).

    {{ ['nl', 'en'] | bazarr_language_profile(profile_id, 'Dutch and English') }}
"""


def bazarr_settings_form(wanted, current):
    form = {}
    for section, values in wanted.items():
        for key, value in values.items():
            if current.get(section, {}).get(key) != value:
                form["settings-%s-%s" % (section, key)] = str(value).lower() if isinstance(value, bool) else value
    return form


def bazarr_language_profile(languages, profile_id, name):
    items = [{"id": i, "language": language, "audio_exclude": "False", "audio_only_include": "False",
              "hi": "False", "forced": "False"} for i, language in enumerate(languages, 1)]
    return {"profileId": profile_id, "name": name, "cutoff": None, "items": items,
            "mustContain": [], "mustNotContain": [], "originalFormat": None, "tag": None}


class FilterModule:
    def filters(self):
        return {"bazarr_settings_form": bazarr_settings_form,
                "bazarr_language_profile": bazarr_language_profile}
