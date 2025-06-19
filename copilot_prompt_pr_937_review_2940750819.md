# Code Review Fixes for PR #937

Repository: cbsi-cmg/ngcms
PR: https://github.com/cbsi-cmg/ngcms/pull/937
Review ID: 2940750819
Review Link: https://github.com/cbsi-cmg/ngcms/pull/937#pullrequestreview-2940750819

I need help addressing the following review comments and implementing the requested changes:

## 🔍 Review Comments

🔴 **@vknowles-rv** (CHANGES_REQUESTED):
*Review ID: 2940750819*

Overall, nice approach with the composable and the prettier adjustments are much needed.

It can be simplified by scrapping the catalogOffersDisabled computed and watching a specific property on the version ref.

There is a bug where typeName isn't tracking, and it's a `nit` whether you want to address it here or keep your getTypeNameFromId call. If you fix that bug, You can trim a lot off of your composable and narrow it to what it truly cares about (a change on version ref).

---

## 📝 Inline Code Comments

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-listicle/Block.vue`:
To @nicbarajas's point, catalogOffersDisabled can be scrapped and this can be simplified to `useCatalogOffers(model)`. Your toggle to false in your composable will be enough.

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-listicle/Block.vue`:
Same here, scrap this.

It doesn't look to be affecting here, but we do not want it disabled anyhow. readonly is good enough

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-listicle/Block.vue`:
Back to readonly please

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-listicle/Block.vue`:
It's likely throwing an error since it isn't passed down from defineComponent. Either way, it can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-reviewcard/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-reviewcard/Block.vue`:
readonly and disabled changes can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-reviewcard/Context.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/broadband-reviewcard/Context.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/commercepromo/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/commercepromo/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/cross-content-listicle/Block.vue`:
const object destruction can go. useCatalogOffers call is good enough. 

---

📍 **@vknowles-rv** in `src/components/editor/blocks/cross-content-listicle/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/cross-content-listicle/PublishedContext.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/cross-content-listicle/PublishedContext.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/listicle/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/listicle/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/listicle/Context.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/listicle/Context.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/reviewcard/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/components/editor/blocks/reviewcard/Block.vue`:
can go

---

📍 **@vknowles-rv** in `src/composables/useCatalogOffers.ts`:
can go. IMO, watch is good enough

---

📍 **@vknowles-rv** in `src/composables/useCatalogOffers.ts`:
nit: I see why you needed to do this. typeName is only set on load. It becomes out of date as the user makes changes.

An additional step would be to keep it sync'd, as it's currently a bug. Then you can get rid of all this fluff and have a watch on version.value.typeName with the usePricing to false. 46 lines of code down to ~9!

hint: add an @update:model-value to v-autocomplete in `src/modules/article/components/context-items/ArticleVersion.vue` and do your getTypeName search and version.value.typeName = there. typeList is already available to leverage.

---

📍 **@vknowles-rv** in `src/composables/useCatalogOffers.ts`:
nit: Nice type narrowing here! I wonder if TechProductShortcode interface would work.

---

📍 **@vknowles-rv** in `src/composables/useCatalogOffers.ts`:
I'd move this to src/modules/article/composables.ts since it's very article specific.

---

📍 **@vknowles-rv** in `src/composables/useCatalogOffers.ts`:
computed is extra overhead.

A watch on () => version.value.type should suffice (or typeName if you do the nit above).

---

📍 **@vknowles-rv** in `.prettierrc`:
🔥 

---

## 🎯 What I Need Help With

Please help me:

1. **Analyze** each comment and identify the specific issues raised
2. **Prioritize** the changes needed (critical bugs → improvements → style)
3. **Provide** specific code changes to address each concern
4. **Explain** how each change addresses the reviewer's feedback

## Context:
- PR Link: https://github.com/cbsi-cmg/ngcms/pull/937
- Specific review: https://github.com/cbsi-cmg/ngcms/pull/937#pullrequestreview-2940750819

Focus on actionable changes I can implement immediately. If any comment is unclear, please ask for clarification on what specific change is needed.

Let's work through these systematically, starting with the most critical issues.
