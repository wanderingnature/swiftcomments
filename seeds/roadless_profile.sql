-- roadless_profile.sql: the sentiment meanings, the 17 topics and the v1 prompt
-- Generated from rtca db/seeds/roadless_profile.sql at the tag reproduction-source,
-- for SQLite: {analysis}. dropped, ARRAY[...] as JSON text, the dollar-quoted
-- template as a quoted string. Loaded by scripts/make_schema.py.

-- Sentiment meanings: SUPPORT = supports the proposed action, which for this
-- project is RESCINDING the 2001 Roadless Rule.
UPDATE sentiment SET
    meaning = 'Favors rescinding the 2001 Roadless Area Conservation Rule (supports the proposed change)',
    display_label = 'Supports rescission'
WHERE sentiment_id = 1;
UPDATE sentiment SET
    meaning = 'Opposes rescinding the 2001 Roadless Rule (wants to keep current protections)',
    display_label = 'Opposes rescission'
WHERE sentiment_id = 2;
UPDATE sentiment SET
    meaning = 'Unclear position, mixed views, or no clear stance',
    display_label = 'Neutral / unclear'
WHERE sentiment_id = 3;

-- Topic taxonomy (17 topics: 15 from consolidated_topics.json + wildlife_habitat, tribal_sovereignty).
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('environmental_protection_biodiversity', 'Comments emphasizing the protection of ecosystems, biodiversity, wildlife habitats, and overall environmental health in roadless areas, including concerns about ecosystem disruption, habitat fragmentation, and species conservation.',
        '["biodiversity", "wildlife habitat", "ecosystem health", "conservation", "habitat preservation", "ecosystem disruption", "endangered species", "ecosystem connectivity", "natural beauty", "ecosystem services", "ecosystem preservation", "species conservation", "wildlife", "habitat protection", "ecosystems", "natural resources", "wildlife corridors", "ecological integrity", "stream pollution", "sediment runoff", "pollution prevention", "wild places", "unspoiled nature"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('recreation_tourism_public_use', 'Comments highlighting the value of roadless areas for recreational activities such as hiking, hunting, fishing, camping, climbing, and wildlife watching, and the importance of preserving these opportunities for public enjoyment and outdoor tourism.',
        '["recreation", "backcountry", "outdoor activities", "hunting", "fishing", "wildlife watching", "wilderness areas", "tourism", "hiking trails", "camping", "recreational opportunities", "backcountry recreation", "remote areas", "wilderness experience", "climbing", "wildlife viewing", "recreational use", "outdoor recreation", "hiking", "backcountry activities", "recreation access", "nature lovers", "recreational activities", "irreplaceable experience", "leisure", "revenue generation", "job creation", "local economy", "ecotourism", "recreation-based economy"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('resource_development_extraction', 'Comments supporting or opposing the use of roadless areas for resource extraction including logging, mining, oil and gas development, and other industrial activities, often tied to economic development or environmental concerns.',
        '["resource extraction", "logging industry", "timber", "mining", "oil and gas", "energy development", "natural resources", "corporate interests", "profit", "industry", "responsible logging", "sustainable forestry", "economic growth", "local timber", "private companies", "exploitation", "short-term gains", "economic exploitation", "timber harvest", "development"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('forest_management_wildfire', 'Comments discussing forest health, fire risk, wildfire prevention, fuel reduction, and ecosystem resilience, with differing views on whether roadless rule changes improve or hinder effective forest management and fire mitigation.',
        '["forest management", "fire risk", "wildfire risk", "hazardous fuels", "fire prevention", "fire suppression", "fuels reduction", "forest health", "ecosystem restoration", "fire management", "forest disease", "insect infestations", "resilience", "thinning", "human-caused fires", "mitigation", "wildfire management", "wildfire", "fire risk reduction", "wildland-urban interface", "community protection", "safety", "risk reduction", "public safety", "wildfires", "road development"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('climate_carbon_storage', 'Comments addressing the role of roadless forests in climate change mitigation through carbon sequestration and storage, and concerns about increased emissions, ecosystem disruption, and reduced climate resilience due to development.',
        '["carbon sequestration", "carbon storage", "climate change", "greenhouse gas emissions", "carbon sink", "climate resilience", "ecosystem resilience", "rising temperatures", "global warming", "climate change mitigation", "carbon emissions", "sustainability", "ecological resilience", "climatic change", "long-term impacts", "natural disaster mitigation"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('public_land_access_rights', 'Comments focused on public access to national forests and roadless areas for recreation, conservation, and cultural use, emphasizing the democratic right to enjoy and steward public lands while respecting indigenous rights and future generations.',
        '["public access", "access to public lands", "public lands", "recreation opportunities", "wilderness areas", "conservation", "public benefit", "trails", "infrastructure", "community engagement", "public use", "hiking", "camping", "hunting", "backcountry", "public ownership", "public trust", "future generations", "property rights", "private property rights", "land ownership", "public good", "indigenous rights", "tribal interests", "cultural heritage", "sacred sites", "self-governance", "local control", "federal government"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('governance_policy_process', 'Comments addressing the transparency, accountability, and inclusiveness of the rulemaking process, including public participation, stakeholder engagement, and democratic decision-making in forest policy, with concerns about government accountability and procedural integrity.',
        '["public involvement", "governance processes", "stakeholder", "EIS", "rulemaking process", "accountability", "transparency", "public input", "public participation", "decision-making", "engagement", "governance structure", "policy-making", "public comment", "government accountability", "public trust", "fiduciary responsibility", "public opinion", "democratic will", "public confidence", "policy legitimacy", "due process", "stakeholder engagement", "procedural concerns", "environmental impact statement", "comment period"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('economic_impact_fiscal', 'Comments discussing the economic implications of the rule change, including job creation, local economic development, tourism revenue, taxpayer costs related to road construction and maintenance, and fiscal responsibility concerns.',
        '["economic development", "local economies", "job creation", "tax revenue", "community well-being", "tourism", "economic benefits", "revenue generation", "taxpayer costs", "road maintenance", "fiscal responsibility", "deferred maintenance backlog", "economic impacts", "rural development", "community development", "taxpayer burden", "maintenance costs", "Forest Service resources", "budgeting", "infrastructure costs", "strain on Forest Service resources", "personnel", "existing roads", "new roads"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('scientific_research_evidence', 'Comments citing scientific studies, data, and research to support arguments about the ecological, climatic, and management impacts of the proposed rule change, emphasizing evidence-based policy and scientific consensus.',
        '["scientific research", "data", "studies", "evidence", "research", "science", "environmental impact assessments", "carbon sequestration", "biodiversity", "ecosystem health", "climate change", "peer-reviewed", "scientific evidence", "scientific basis", "expert opinions", "scientific consensus", "research findings", "data-driven", "scientific integrity", "objectivity", "ecosystem management", "ecological sustainability"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('cultural_heritage_indigenous', 'Comments addressing the cultural, spiritual, and historical significance of roadless areas to Indigenous peoples and broader communities, including tribal sovereignty, ancestral lands, traditional practices, cultural preservation, and spiritual values.',
        '["indigenous rights", "tribal sovereignty", "cultural resources", "ancestral lands", "traditional practices", "Native American", "cultural significance", "cultural preservation", "traditional knowledge", "tribal lands", "spiritual values", "cultural heritage", "cultural uses", "traditional uses", "subsistence hunting", "gathering", "Indigenous communities", "tribal perspectives", "sacred sites", "national identity", "natural heritage", "conservation legacy", "public health", "mental well-being", "spiritual connection"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('legal_regulatory_framework', 'Comments discussing the legal basis of the Roadless Rule, including federal laws, regulations, court decisions, agency authority, compliance requirements, and how proposed changes align or conflict with existing statutes and regulatory processes.',
        '["regulatory framework", "laws", "regulations", "policies", "rulemaking", "federal law", "court decisions", "agency authority", "legislation", "governance", "administrative matters", "regulatory matters", "policy implications", "regulation", "compliance", "consistency", "policy", "regulatory process", "constitutional considerations", "legal considerations", "environmental impact statement", "established policies"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('water_quality_quantity', 'Comments emphasizing the importance of roadless areas in protecting watersheds, ensuring clean water supply, preventing sedimentation and pollution, maintaining aquatic ecosystems, and addressing water scarcity concerns.',
        '["water quality", "clean water", "water supply", "aquatic ecosystems", "sedimentation", "pollution", "water conservation", "watershed management", "water treatment costs", "water scarcity", "water pollution", "drinking water", "air pollution"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('public_health_wellbeing', 'Comments linking the protection of roadless areas to human health, including clean air, clean water, mental and physical wellness, quality of life, and the therapeutic benefits of nature access.',
        '["public health", "human health", "clean water", "air quality", "wellness", "mental health", "physical health", "quality of life", "well-being", "human well-being"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('national_security_public_safety', 'Comments discussing the implications of the proposed rule change for national security, military operations, border security, emergency response, public safety including search and rescue, and national resilience considerations.',
        '["national security", "military operations", "defense strategies", "homeland security", "border security", "public safety", "terrorism", "law enforcement", "emergency response", "search and rescue", "public services", "resilience", "sovereignty", "defense", "invasive species", "ecosystem integrity", "safety", "wilderness"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('public_opinion_support', 'Comments referencing public sentiment, opinion polls, grassroots movements, and broad-based support or opposition to the Roadless Rule and the proposed changes, emphasizing democratic legitimacy and community engagement.',
        '["public opinion", "popular support", "public support", "opposition", "community engagement", "advocacy", "grassroots movement", "consensus", "American public", "personal experiences", "community impact", "cultural heritage", "community values", "state government", "local government", "social impact", "local community"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('wildlife_habitat', 'Comments focused specifically on wildlife habitat in roadless areas — habitat connectivity, migration and wildlife corridors, denning, nesting, and spawning grounds, winter range, and species-specific range — and how road building, logging, and development fragment or degrade that habitat.',
        '["wildlife habitat", "habitat fragmentation", "habitat connectivity", "migration corridors", "wildlife corridors", "winter range", "denning", "nesting", "spawning habitat", "big game", "elk", "deer", "salmon", "trout", "fisheries", "threatened and endangered species", "critical habitat", "habitat loss", "roadless habitat", "species range"]',
        'opposes_proposal', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;
INSERT INTO topics (topic_name, description, key_phrases, typical_position, is_active)
VALUES ('tribal_sovereignty', 'Comments centering tribal sovereignty and the government-to-government relationship — treaty and reserved rights, consultation obligations, co-management, ceded and ancestral lands, trust responsibility, and tribal authority over roadless-area decisions — distinct from the cultural and spiritual significance covered by cultural_heritage_indigenous.',
        '["tribal sovereignty", "treaty rights", "reserved rights", "government-to-government", "nation-to-nation", "tribal consultation", "co-management", "ceded lands", "ancestral lands", "trust responsibility", "self-determination", "tribal nations", "sovereign nations", "free prior and informed consent", "tribal authority", "federal trust obligation"]',
        'mixed', true)
ON CONFLICT (topic_name) DO UPDATE SET description = EXCLUDED.description, key_phrases = EXCLUDED.key_phrases, typical_position = EXCLUDED.typical_position, is_active = true;

-- The sentiment/topic classification prompt (exactly one active per kind).
INSERT INTO prompts
    (prompt_kind, prompt_name, system_prompt, user_prompt_template,
     model_name, model_parameters, version, is_active, notes)
VALUES (
    'sentiment_topic',
    'roadless_rescission_v1',
    'You are an expert text classification system specialized in analyzing public policy comments. Your task is to accurately classify content into predefined topic categories and assess sentiment toward specific policy proposals with high precision. Always respond with valid JSON only, following the exact format specified.',
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

    Return ONLY VALID JSON IN THE FORMAT ABOVE. No explanations, no additional text.

    Comment: "{comment_text}"',
    'Qwen/Qwen2.5-7B-Instruct-Turbo',
    '{"max_tokens": 2048, "temperature": 0.0, "top_p": 1.0}',
    1,
    true,
    'v1 tuned to the FS-2025-0001 proposed rule (Federal Register anchor). model_name and params match the Chaco profile; large batches run on the shared Together dedicated endpoint (BF16) via classify_mode=cloud.'
);
