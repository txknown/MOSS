"use strict";

import { createElement } from "../dom.js?v=24";


const IMAGE_SIZE_PRESETS = {
  small: "320px",
  medium: "560px",
  large: "100%",
};


function applyImageSize(panel, node) {
  const rawSize = String(node.attributes?.size || "large").trim();
  let size = IMAGE_SIZE_PRESETS[rawSize.toLowerCase()] || rawSize;
  if (/^(?:\d+(?:\.\d+)?|\.\d+)$/.test(size)) size = `${size}px`;
  if (size && CSS.supports("width", size)) panel.style.width = size;
}


export function createMaterialRenderers({ makeHeadingLink }) {
  function renderImage(node, path, direct = false) {
    const panel = createElement("figure", "image-panel");
    applyImageSize(panel, node);
    const frame = createElement("div", "image-frame");
    const title = node.display_title || node.title || node.id;

    const showMissing = () => {
      frame.replaceChildren(
        createElement(
          "div",
          "missing-image",
          node.material_status === "blocked"
            ? "This image source is outside MOSS materials and cannot be opened."
            : "Image material is missing.",
        ),
      );
    };

    if (
      node.material_exists &&
      typeof node.material_url === "string" &&
      node.material_url.startsWith("/materials/")
    ) {
      const image = createElement("img");
      image.alt = node.title || node.id;
      image.loading = "lazy";
      image.decoding = "async";
      image.addEventListener("error", showMissing, { once: true });
      image.src = node.material_url;
      const imageLink = direct
        ? createElement("a", "image-link")
        : makeHeadingLink(node, path);
      imageLink.className = "image-link";
      if (direct) {
        imageLink.href = node.material_url;
        imageLink.target = "_blank";
        imageLink.rel = "noopener";
        imageLink.setAttribute("aria-label", `Open full-size ${title}`);
      } else {
        imageLink.replaceChildren();
        imageLink.setAttribute("aria-label", `Open ${title} image node`);
      }
      imageLink.append(image);
      frame.append(imageLink);
    } else {
      showMissing();
    }

    if (direct) {
      const caption = createElement("figcaption", "image-caption");
      caption.textContent = title;
      panel.append(frame, caption);
    } else {
      panel.append(frame);
    }
    return panel;
  }

  return { renderImage };
}
