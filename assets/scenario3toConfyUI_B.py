"""
comfy_builder_v2.py — Improved ComfyUI API Pipeline for Cyberpunk Storyboard
=============================================================================

CHANGES FROM v1:

1. CHARACTER BIBLE
   Centralized identity descriptors. Exact same tokens injected every shot.
   Eliminates the drift caused by per-prompt paraphrasing.

2. DUAL CLIP ENCODING (BUG FIX)
   CLIPTextEncodeFlux takes clip_l + t5xxl separately, NOT a single "text".
   - clip_l  → character identity anchors + shot type  (77-token CLIP-L)
   - t5xxl   → full scene with Bible prefix injected   (T5-XXL, long context)

3. PER-SHOT PARAMETER TUNING
   ControlNet strength and PuLID weight now vary by shot type:
   - Wide/medium-wide:  lower PuLID (face small in frame), softer ControlNet
   - Close-up/macro:    higher PuLID (face dominates), tighter ControlNet
   - OTS / two-shot:    differentiated weights per character by screen presence

4. IP-ADAPTER LAYER
   Secondary identity anchor alongside PuLID. PuLID encodes face geometry;
   IP-Adapter encodes broader visual identity (clothing, posture, palette).
   Turnaround image → IP-Adapter, face crop → PuLID.

5. FACE CROP REFERENCES
   PuLID works best with tight face crops, not full turnarounds.
   Added separate ref_face entries in the Bible. Pre-crop offline or
   swap in a FaceDetectCrop node if you want it automated.

6. CAMERA PARAMETERS
   Per-shot focal_length, pitch, yaw matching actual described framing.
   No more naive yaw = 15 * shot_id.

7. RESOLUTION BUMP
   1024×576 → 1344×768 (proper 16:9 for cinematic storyboards).

8. NEGATIVE CONDITIONING (structural)
   Flux at cfg=1.0 barely uses it, but it's wired correctly for the
   case where you raise guidance or switch to a cfg>1 sampler.

NOTE ON MULTI-CHARACTER SHOTS:
   PuLID is applied sequentially (John → Elena). The second application
   partially overrides the first. This is a known limitation. Mitigations:
   - Lower weight on the background/silhouette character
   - Higher weight on the focal character
   - For production quality, consider Flux Kontext for frame-to-frame
     consistency (condition on previous generated shots).
   - Regional attention masking (when mature for Flux) would be ideal.
"""

import json

# ═══════════════════════════════════════════════════════════════════════════════
# CHARACTER BIBLE — Single source of truth. FROZEN across all shots.
# Any per-shot variation (action, expression) goes in the shot's t5xxl_scene.
# ═══════════════════════════════════════════════════════════════════════════════

CHARACTER_BIBLE = {
    "john": {
        # clip_l: compact identity tokens — CLIP-L friendly, < 35 tokens
        "clip_l": (
            "John, rugged male detective early 50s, sharp defined jawline, "
            "deep-set tired grey eyes, short cropped grey-brown hair, "
            "weathered olive skin with stubble, dark brown leather trench coat"
        ),
        # t5xxl: rich natural-language description — T5-XXL parses long detail
        "t5xxl": (
            "John is a rugged middle-aged male detective in his early fifties. "
            "He has a distinctly sharp and defined jawline, deep-set tired grey "
            "eyes with visible crow's feet, short cropped grey-brown hair "
            "receding slightly at the temples, weathered olive skin with subtle "
            "day-old stubble. He wears a worn dark brown leather trench coat "
            "over a rumpled off-white dress shirt with the collar loosened."
        ),
        "ref_image": "john_turnaround.png",    # full body → IP-Adapter
        "ref_face": "john_face_crop.png",       # tight face crop → PuLID
    },
    "elena": {
        "clip_l": (
            "Elena, sleek female tech informant mid 30s, sharp angular features, "
            "clean defined jawline, dark calculating almond eyes, "
            "short asymmetric black hair with undercut, pale skin, dark tech jacket"
        ),
        "t5xxl": (
            "Elena is a sleek female tech informant in her mid-thirties. "
            "She has sharp angular facial features with high cheekbones, a clean "
            "defined jawline, dark calculating almond-shaped eyes, short asymmetric "
            "black hair with a precise undercut on the left side, pale skin with "
            "subtle cool undertones. She wears a fitted matte-black tech-fabric "
            "jacket with minimal geometric seam detailing."
        ),
        "ref_image": "elena_turnaround.png",
        "ref_face": "elena_face_crop.png",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# SHOT DEFINITIONS — Dual-prompt architecture + per-shot tuning
# ═══════════════════════════════════════════════════════════════════════════════
# Template variables resolved at build time:
#   {john_t5xxl}   → CHARACTER_BIBLE["john"]["t5xxl"]
#   {john_clip_l}  → CHARACTER_BIBLE["john"]["clip_l"]
#   {elena_t5xxl}  → CHARACTER_BIBLE["elena"]["t5xxl"]
#   {elena_clip_l} → CHARACTER_BIBLE["elena"]["clip_l"]

SHOT_DATAS = {
    1: {
        "title": "Shot_1_Cafe_Wide",
        "clip_l_scene": (
            "wide establishing shot, retro-futuristic cyberpunk cafe, "
            "red neon glow, atmospheric haze, dark corner table, cinematic"
        ),
        "t5xxl_scene": (
            "{john_t5xxl} He sits completely alone at a wet dark corner table "
            "in a retro-futuristic cyberpunk cafe. Above him a buzzing flickering "
            "red neon sign casts intense crimson glow and harsh geometric shadows "
            "across his face and trench coat. The air is thick with atmospheric "
            "haze and faint cigarette smoke. Cinematic wide angle establishing "
            "shot, anamorphic lens flare, deep contrast, photorealistic 8k "
            "film texture."
        ),
        "characters": ["john"],
        "camera": {"focal_length": 24.0, "pitch": -5.0, "yaw": 0.0},
        "cnet_strength": 0.60,       # wide shot → softer spatial lock
        "pulid_weights": {"john": 0.55},     # face is small in frame
        "ipadapter_weights": {"john": 0.50}, # body/clothing anchor helps here
        "guidance": 3.5,
    },

    2: {
        "title": "Shot_2_Cafe_Medium_OTS",
        "clip_l_scene": (
            "medium over-the-shoulder shot, dim neon-lit cafe interior, "
            "red neon ambient glow, faint blue screen light, shallow depth of field"
        ),
        "t5xxl_scene": (
            "Cinematic medium over-the-shoulder shot inside a dim neon-lit cafe. "
            "In the foreground the dark silhouette of {john_clip_l} is seen from "
            "behind his right shoulder, slightly out of focus. Opposite him at the "
            "table, {elena_t5xxl} Her face is partially illuminated by ambient red "
            "neon glow and a faint blue light reflecting from an unseen screen "
            "below frame. She has a sharp calculating expression, studying "
            "something on the table. Muted cyberpunk color palette, cinematic "
            "film grain, shallow depth of field, sharp focus on Elena's face, "
            "35mm anamorphic photography."
        ),
        "characters": ["john", "elena"],
        "camera": {"focal_length": 35.0, "pitch": 0.0, "yaw": 35.0},
        "cnet_strength": 0.75,
        # John is a silhouette/back → low PuLID. Elena is focal → high.
        "pulid_weights": {"john": 0.40, "elena": 0.85},
        "ipadapter_weights": {"john": 0.35, "elena": 0.60},
        "guidance": 3.5,
    },

    3: {
        "title": "Shot_3_Cafe_Closeup",
        "clip_l_scene": (
            "extreme close-up portrait, neon cafe, glowing data drive on table, "
            "neon red and cyan light on face, macro detail, shallow bokeh"
        ),
        "t5xxl_scene": (
            "Intense cinematic macro close-up shot. {elena_t5xxl} She is leaning "
            "forward slightly with piercing focused eyes, explaining a glowing "
            "high-tech decrypted data drive resting on the dark table surface. "
            "Neon red from the left and cold cyan from the right catch the sharp "
            "contours of her cheekbones and jawline, and the intricate circuit "
            "textures of the drive. Extreme detail on skin textures and "
            "micro-expressions, shallow depth of field with beautiful bokeh of "
            "blurred warm cafe interior behind, 8k raw movie still."
        ),
        "characters": ["elena"],
        "camera": {"focal_length": 85.0, "pitch": 0.0, "yaw": 5.0},
        "cnet_strength": 0.85,       # close-up → tighter spatial lock
        "pulid_weights": {"elena": 0.95},    # face IS the shot
        "ipadapter_weights": {"elena": 0.70},
        "guidance": 3.5,
    },

    4: {
        "title": "Shot_4_Garage_Medium_Wide",
        "clip_l_scene": (
            "medium wide shot, underground concrete parking garage, "
            "brutalist pillars, rain-slicked floor, fluorescent flicker, cold tones"
        ),
        "t5xxl_scene": (
            "Cinematic medium wide atmospheric shot of an underground concrete "
            "parking garage. {john_t5xxl} He walks cautiously through the vast "
            "dark space, stepping past massive brutalist concrete pillars. "
            "The environment is damp with rain-slicked concrete floors reflecting "
            "distant flickering overhead industrial fluorescent lights. Harsh "
            "shadows, deep blacks, cold desaturated color grade, cinematic "
            "suspenseful atmosphere, sharp focus on John's alert posture."
        ),
        "characters": ["john"],
        "camera": {"focal_length": 28.0, "pitch": -3.0, "yaw": 10.0},
        "cnet_strength": 0.65,
        "pulid_weights": {"john": 0.65},
        "ipadapter_weights": {"john": 0.55},
        "guidance": 3.5,
    },

    5: {
        "title": "Shot_5_Garage_TwoShot",
        "clip_l_scene": (
            "medium two-shot, dark cold concrete garage, two people facing, "
            "overhead industrial lights, long dramatic shadows, wet floor, tense"
        ),
        "t5xxl_scene": (
            "Cinematic medium two-shot in a dark cold concrete parking garage. "
            "On the left side of frame, {elena_t5xxl} She has just appeared from "
            "behind a massive concrete pillar. On the right side of frame, "
            "{john_t5xxl} He has stopped abruptly in his tracks, body tense. "
            "Both characters face each other in balanced cinematic composition "
            "with visible tension. The scene is lit by harsh high-contrast "
            "overhead industrial lights casting long dramatic shadows across "
            "the wet floor. Photorealistic 8k, raw texture, cinematic still."
        ),
        "characters": ["john", "elena"],
        "camera": {"focal_length": 40.0, "pitch": 0.0, "yaw": 0.0},
        "cnet_strength": 0.80,
        "pulid_weights": {"john": 0.75, "elena": 0.75},
        "ipadapter_weights": {"john": 0.55, "elena": 0.55},
        "guidance": 3.5,
    },

    6: {
        "title": "Shot_6_Garage_Closeup",
        "clip_l_scene": (
            "dramatic close-up portrait, dark parking garage, "
            "high-tech device emitting blue glow on face, deep shadows"
        ),
        "t5xxl_scene": (
            "Cinematic dramatic close-up shot in the dark parking garage. "
            "{john_t5xxl} He is looking down intently at a small high-tech device "
            "held in both hands at chest level. His rugged face and focused "
            "expression are brilliantly illuminated from below by the cold "
            "emissive blue glow radiating from the device screen. The background "
            "is a dark out-of-focus concrete structure with deep shadows. "
            "Intricate skin texture details, realistic light reflection in his "
            "eyes, 8k resolution cinematic film capture."
        ),
        "characters": ["john"],
        "camera": {"focal_length": 85.0, "pitch": 2.0, "yaw": -5.0},
        "cnet_strength": 0.85,
        "pulid_weights": {"john": 0.95},
        "ipadapter_weights": {"john": 0.70},
        "guidance": 3.5,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT RESOLVER — Injects Character Bible into shot templates
# ═══════════════════════════════════════════════════════════════════════════════

def _resolve_prompt(template: str) -> str:
    """Replace {name_t5xxl} and {name_clip_l} with Bible entries."""
    result = template
    for name, bible in CHARACTER_BIBLE.items():
        result = result.replace(f"{{{name}_t5xxl}}", bible["t5xxl"])
        result = result.replace(f"{{{name}_clip_l}}", bible["clip_l"])
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def generate_comfy_api_pipeline(output_filename="workflow_api_v2.json"):
    """Build the full ComfyUI API-format execution graph."""

    # ── GLOBAL ASSET HUB ─────────────────────────────────────────────────────
    graph = {
        # Core model
        "1": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "flux1-dev.safetensors"},
        },
        "2": {
            "class_type": "DualCLIPLoader",
            "inputs": {
                "clip_name1": "t5xxl_fp16.safetensors",
                "clip_name2": "clip_l.safetensors",
            },
        },
        "3": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "ae.safetensors"},
        },

        # Spatial guidance
        "4": {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": "flux-depth-controlnet.safetensors"},
        },

        # IP-Adapter model + CLIP vision (loaded once, applied per-shot)
        # Adjust filenames to match your cubiq/IPAdapter-plus installation
        "5": {
            "class_type": "IPAdapterModelLoader",
            "inputs": {"ipadapter_file": "ip-adapter_flux.safetensors"},
        },
        "6": {
            "class_type": "CLIPVisionLoader",
            "inputs": {"clip_name": "sigclip_vision_384.safetensors"},
        },

        # ── CHARACTER REFERENCE IMAGES ──
        # Full turnarounds → IP-Adapter (body/clothing/posture)
        "10": {
            "class_type": "LoadImage",
            "inputs": {"image": CHARACTER_BIBLE["john"]["ref_image"]},
        },
        "11": {
            "class_type": "LoadImage",
            "inputs": {"image": CHARACTER_BIBLE["elena"]["ref_image"]},
        },
        # Tight face crops → PuLID (facial geometry/identity)
        # Pre-crop these offline at ~512×512 centered on face.
        # Alternative: add FaceDetectCrop nodes here to automate.
        "12": {
            "class_type": "LoadImage",
            "inputs": {"image": CHARACTER_BIBLE["john"]["ref_face"]},
        },
        "13": {
            "class_type": "LoadImage",
            "inputs": {"image": CHARACTER_BIBLE["elena"]["ref_face"]},
        },

        # ── 3D DEPTH PIPELINE ──
        "20": {
            "class_type": "Load3DMesh",
            "inputs": {"mesh_path": "generic_humanoid.obj"},
        },
        "21": {
            "class_type": "3DPoseEditor",
            "inputs": {"mesh": ["20", 0]},
        },
    }

    # Lookup: character name → node IDs for references
    CHAR_NODES = {
        "john":  {"turnaround": "10", "face": "12"},
        "elena": {"turnaround": "11", "face": "13"},
    }

    node_counter = 200

    for shot_id, data in SHOT_DATAS.items():

        # ── RESOLVE PROMPTS ──────────────────────────────────────────────────
        resolved_t5xxl = _resolve_prompt(data["t5xxl_scene"])

        # Composite clip_l = character Bible clip_l tokens + scene clip_l tokens
        char_clip_parts = [
            CHARACTER_BIBLE[c]["clip_l"] for c in data["characters"]
        ]
        composite_clip_l = ". ".join(char_clip_parts) + ". " + data["clip_l_scene"]

        # ── ALLOCATE NODE IDs ────────────────────────────────────────────────
        # Fixed nodes for this shot block
        n = node_counter
        id_clip_pos = str(n)
        id_clip_neg = str(n + 1)
        id_camera   = str(n + 2)
        id_render   = str(n + 3)
        id_cnet     = str(n + 4)
        id_latent   = str(n + 5)
        id_sampler  = str(n + 6)
        id_decode   = str(n + 7)
        id_save     = str(n + 8)
        # Dynamic character nodes start at offset 10
        dyn_offset  = 10

        # ── POSITIVE CONDITIONING (DUAL CLIP — THE FIX) ─────────────────────
        graph[id_clip_pos] = {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": composite_clip_l,     # identity tokens + shot keywords
                "t5xxl": resolved_t5xxl,        # full scene with Bible injection
                "guidance": data["guidance"],
            },
        }

        # ── NEGATIVE CONDITIONING ────────────────────────────────────────────
        # Flux at cfg=1.0 barely uses this. Wired correctly for when you
        # experiment with cfg>1 or guidance-distilled samplers.
        neg_t5xxl = (
            "blurry, deformed face, extra fingers, mutated hands, "
            "poorly drawn face, disfigured, bad anatomy, wrong proportions"
        )
        if len(data["characters"]) == 1:
            neg_t5xxl += ", multiple people, extra person, crowd"
        graph[id_clip_neg] = {
            "class_type": "CLIPTextEncodeFlux",
            "inputs": {
                "clip": ["2", 0],
                "clip_l": "",
                "t5xxl": neg_t5xxl,
                "guidance": data["guidance"],
            },
        }

        # ── 3D CAMERA → DEPTH MAP ───────────────────────────────────────────
        cam = data["camera"]
        graph[id_camera] = {
            "class_type": "OrbitCamera",
            "inputs": {
                "mesh": ["21", 0],
                "focal_length": cam["focal_length"],
                "pitch": cam["pitch"],
                "yaw": cam["yaw"],
            },
        }
        graph[id_render] = {
            "class_type": "Render3DMeshToDepth",
            "inputs": {"mesh": [id_camera, 0]},
        }

        # ── MODEL CONDITIONING CHAIN ────────────────────────────────────────
        # Each node takes the previous model output, forming:
        # UNETLoader → ControlNet → PuLID(char1) → PuLID(char2) →
        #              IP-Adapter(char1) → IP-Adapter(char2) → KSampler

        current_model = ["1", 0]  # start from base UNET

        # ControlNet (depth spatial guidance)
        graph[id_cnet] = {
            "class_type": "ApplyControlNet",
            "inputs": {
                "model": current_model,
                "control_net": ["4", 0],
                "image": [id_render, 0],
                "strength": data["cnet_strength"],
            },
        }
        current_model = [id_cnet, 0]

        # PuLID per character (face geometry identity)
        for i, char_name in enumerate(data["characters"]):
            nid = str(n + dyn_offset + i)
            graph[nid] = {
                "class_type": "ApplyPuLIDFlux",
                "inputs": {
                    "model": current_model,
                    "image": [CHAR_NODES[char_name]["face"], 0],
                    "weight": data["pulid_weights"][char_name],
                },
            }
            current_model = [nid, 0]

        # IP-Adapter per character (broader visual identity)
        ipa_base = dyn_offset + len(data["characters"])
        for i, char_name in enumerate(data["characters"]):
            nid = str(n + ipa_base + i)
            graph[nid] = {
                "class_type": "IPAdapterApply",
                "inputs": {
                    "model": current_model,
                    "ipadapter": ["5", 0],
                    "clip_vision": ["6", 0],
                    "image": [CHAR_NODES[char_name]["turnaround"], 0],
                    "weight": data["ipadapter_weights"][char_name],
                    "weight_type": "linear",
                },
            }
            current_model = [nid, 0]

        # ── LATENT ───────────────────────────────────────────────────────────
        graph[id_latent] = {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 1344,       # 16:9 cinematic (was 1024×576)
                "height": 768,
                "batch_size": 1,
            },
        }

        # ── KSAMPLER ────────────────────────────────────────────────────────
        graph[id_sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": current_model,
                "positive": [id_clip_pos, 0],
                "negative": [id_clip_neg, 0],
                "latent_image": [id_latent, 0],
                "steps": 30,              # 25 → 30 for better convergence
                "cfg": 1.0,               # Flux: guidance is in text encoder
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "seed": 42 + shot_id,
            },
        }

        # ── VAE DECODE ──────────────────────────────────────────────────────
        graph[id_decode] = {
            "class_type": "VAEDecode",
            "inputs": {
                "samples": [id_sampler, 0],
                "vae": ["3", 0],
            },
        }

        # ── SAVE ────────────────────────────────────────────────────────────
        graph[id_save] = {
            "class_type": "SaveImage",
            "inputs": {
                "images": [id_decode, 0],
                "filename_prefix": data["title"],
            },
        }

        # Generous spacing — 30 IDs per shot block
        node_counter += 30

    # ── SERIALIZE ────────────────────────────────────────────────────────────
    with open(output_filename, "w") as f:
        json.dump(graph, f, indent=2)

    print(
        f"Generated {output_filename}: "
        f"{len(graph)} nodes, {len(SHOT_DATAS)} shots, "
        f"{len(CHARACTER_BIBLE)} characters"
    )


if __name__ == "__main__":
    generate_comfy_api_pipeline()
