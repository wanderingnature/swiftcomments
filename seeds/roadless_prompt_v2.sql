-- roadless_prompt_v2.sql: the sentiment_only topic and the v2 prompt, the active one
-- Generated from rtca db/seeds/roadless_prompt_v2.sql at the tag reproduction-source,
-- for SQLite: {analysis}. dropped, ARRAY[...] as JSON text, the dollar-quoted
-- template as a quoted string. Loaded by scripts/make_schema.py.

INSERT INTO topics (topic_name, description, category, is_active)
VALUES ('sentiment_only',
        'Comments that state a position on the proposal and nothing more: too short or generic to support any topic at confidence >= 0.7 with supporting phrases.',
        'no_topic', true);

UPDATE prompts SET is_active = false
WHERE prompt_kind = 'sentiment_topic' AND is_active;

INSERT INTO prompts
    (prompt_kind, prompt_name, system_prompt, user_prompt_template, model_name,
     model_parameters, version, is_active, notes)
SELECT 'sentiment_topic', 'roadless_rescission_v2', p.system_prompt,
'Analyze this public comment on the USFS proposal to rescind the 2001 Roadless Area Conservation Rule.

    POLICY CONTEXT:
    USDA and the Forest Service propose to rescind the 2001 Roadless Area Conservation Rule
    (36 CFR 294 Subpart B), which prohibits road construction, road reconstruction, and timber
    harvesting across about 58.5 million acres of inventoried roadless areas. Rescission removes
    these national prohibitions and returns management decisions to each national forest''s
    land-management plan; USDA states this allows active management for wildfire, insect and
    disease, and wildland-urban-interface protection, and reduces regulatory burden. The
    state-specific Idaho (Subpart C) and Colorado (Subpart D) rules are NOT affected. Rescission
    by itself authorizes no project and does not mandate logging or road building; any future
    project still requires site-specific NEPA review and must be consistent with the governing
    forest plan.

    CLASSIFICATION APPROACH:
    Determine the commenter''s position on this specific policy proposal:
    - SUPPORT: Favors rescinding the current rule (supports the proposed change)
    - OPPOSE: Opposes rescinding the current rule (wants to keep current restrictions)
    - NEUTRAL: Unclear position, mixed views, or no clear stance

    COMMON SUPPORT THEMES:
    - Wildfire risk reduction, hazardous-fuels and vegetation management, forest health
    - Returning decisions to local/forest-level land-management planning (flexibility)
    - Reducing regulatory burden and duplicative national restrictions
    - Timber supply, jobs, and revenue to the Treasury and local economies
    - Access for minerals and energy development
    - Emergency and administrative access; community and infrastructure protection

    COMMON OPPOSE THEMES:
    - Wildlife habitat, biodiversity, and roadless/wilderness conservation values
    - Concern about increased logging, road building, and industrial development
    - Watershed protection and drinking-water sources
    - Climate change and carbon storage (including the Tongass)
    - Quiet, remote, and backcountry recreation values
    - Tribal sovereignty, treaty and trust responsibility, and adequacy of
      government-to-government consultation
    - Sacred sites, cultural resources, and Alaska Native subsistence (ANILCA Section 810)
    - Preference to keep the 2001 Rule (No Action) or to strengthen protections

    STRENGTH GUIDELINES:
    - HIGH: Clear, direct statement of position
    - MEDIUM: Implied position with supporting reasoning
    - LOW: Weak indicators, ambiguous language

    VALID TOPIC NAMES (use exact names):{topics_list}

    REQUIREMENTS:
    - Only include topics with confidence >= 0.7
    - Comment can match multiple topics
    - Use exact topic names from the list above
    - Include 2-4 supporting phrases per topic
    - Classify sentiment as: SUPPORT|OPPOSE|NEUTRAL with strength: HIGH|MEDIUM|LOW
    - If the comment is too short or generic to support any topic at confidence >= 0.7
      with 2-4 supporting phrases, return exactly one topic named "sentiment_only" with
      confidence 1.0 and an empty supporting_phrases list. Do not include any other
      topics alongside sentiment_only.

    EXAMPLE OUTPUT FORMATS:

    For SUPPORT sentiment:
    {
      "sentiment": "SUPPORT|HIGH",
      "topics": [
        {
          "topic_name": "forest_management_wildfire",
          "confidence": 0.85,
          "supporting_phrases": ["wildfire prevention", "forest health management", "emergency access"]
        }
      ]
    }

    For OPPOSE sentiment:
    {
      "sentiment": "OPPOSE|HIGH",
      "topics": [
        {
          "topic_name": "environmental_protection_biodiversity",
          "confidence": 0.90,
          "supporting_phrases": ["protect wildlife habitat", "preserve wilderness", "maintain biodiversity"]
        }
      ]
    }

    For short comments with no identifiable topics:
    {
      "sentiment": "OPPOSE|HIGH",
      "topics": [
        {
          "topic_name": "sentiment_only",
          "confidence": 1.0,
          "supporting_phrases": []
        }
      ]
    }

    Return ONLY VALID JSON IN THE FORMAT ABOVE. No explanations, no additional text.

    Comment: "{comment_text}"',
       'qwen/qwen3.8-27b', '{"temperature": 0.0, "top_p": 1.0}', 2, true,
       'v1 plus the sentiment_only topic: list entry, rule and example.'
FROM prompts p WHERE p.prompt_name = 'roadless_rescission_v1';
