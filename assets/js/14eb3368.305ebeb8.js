"use strict";(self.webpackChunkoverture_schema=self.webpackChunkoverture_schema||[]).push([[969],{1243:(e,t,s)=>{s.d(t,{A:()=>p});s(6540);var n=s(8215),i=s(7559),a=s(4142),r=s(9169),l=s(8774),c=s(1312),o=s(6025),d=s(4848);function u(e){return(0,d.jsx)("svg",{viewBox:"0 0 24 24",...e,children:(0,d.jsx)("path",{d:"M10 19v-5h4v5c0 .55.45 1 1 1h3c.55 0 1-.45 1-1v-7h1.7c.46 0 .68-.57.33-.87L12.67 3.6c-.38-.34-.96-.34-1.34 0l-8.36 7.53c-.34.3-.13.87.33.87H5v7c0 .55.45 1 1 1h3c.55 0 1-.45 1-1z",fill:"currentColor"})})}const m={breadcrumbHomeIcon:"breadcrumbHomeIcon_YNFT"};function h(){const e=(0,o.A)("/");return(0,d.jsx)("li",{className:"breadcrumbs__item",children:(0,d.jsx)(l.A,{"aria-label":(0,c.translate)({id:"theme.docs.breadcrumbs.home",message:"Home page",description:"The ARIA label for the home page in the breadcrumbs"}),className:"breadcrumbs__link",href:e,children:(0,d.jsx)(u,{className:m.breadcrumbHomeIcon})})})}const b={breadcrumbsContainer:"breadcrumbsContainer_Z_bl"};function x(e){let{children:t,href:s,isLast:n}=e;const i="breadcrumbs__link";return n?(0,d.jsx)("span",{className:i,itemProp:"name",children:t}):s?(0,d.jsx)(l.A,{className:i,href:s,itemProp:"item",children:(0,d.jsx)("span",{itemProp:"name",children:t})}):(0,d.jsx)("span",{className:i,children:t})}function v(e){let{children:t,active:s,index:i,addMicrodata:a}=e;return(0,d.jsxs)("li",{...a&&{itemScope:!0,itemProp:"itemListElement",itemType:"https://schema.org/ListItem"},className:(0,n.A)("breadcrumbs__item",{"breadcrumbs__item--active":s}),children:[t,(0,d.jsx)("meta",{itemProp:"position",content:String(i+1)})]})}function p(){const e=(0,a.OF)(),t=(0,r.Dt)();return e?(0,d.jsx)("nav",{className:(0,n.A)(i.G.docs.docBreadcrumbs,b.breadcrumbsContainer),"aria-label":(0,c.translate)({id:"theme.docs.breadcrumbs.navAriaLabel",message:"Breadcrumbs",description:"The ARIA label for the breadcrumbs"}),children:(0,d.jsxs)("ul",{className:"breadcrumbs",itemScope:!0,itemType:"https://schema.org/BreadcrumbList",children:[t&&(0,d.jsx)(h,{}),e.map(((t,s)=>{const n=s===e.length-1,i="category"===t.type&&t.linkUnlisted?void 0:t.href;return(0,d.jsx)(v,{active:n,index:s,addMicrodata:!!i,children:(0,d.jsx)(x,{href:i,isLast:n,children:t.label})},s)}))]})}):null}},3514:(e,t,s)=>{s.d(t,{A:()=>p});s(6540);var n=s(8215),i=s(4142),a=s(8774),r=s(6654),l=s(1312),c=s(1107);const o={cardContainer:"cardContainer_fWXF",cardTitle:"cardTitle_rnsV",cardDescription:"cardDescription_PWke"};var d=s(4848);function u(e){let{href:t,children:s}=e;return(0,d.jsx)(a.A,{href:t,className:(0,n.A)("card padding--lg",o.cardContainer),children:s})}function m(e){let{href:t,icon:s,title:i,description:a}=e;return(0,d.jsxs)(u,{href:t,children:[(0,d.jsxs)(c.A,{as:"h2",className:(0,n.A)("text--truncate",o.cardTitle),title:i,children:[s," ",i]}),a&&(0,d.jsx)("p",{className:(0,n.A)("text--truncate",o.cardDescription),title:a,children:a})]})}function h(e){let{item:t}=e;const s=(0,i.Nr)(t);return s?(0,d.jsx)(m,{href:s,icon:"\ud83d\uddc3\ufe0f",title:t.label,description:t.description??(0,l.translate)({message:"{count} items",id:"theme.docs.DocCard.categoryDescription",description:"The default description for a category card in the generated index about how many items this category includes"},{count:t.items.length})}):null}function b(e){let{item:t}=e;const s=(0,r.A)(t.href)?"\ud83d\udcc4\ufe0f":"\ud83d\udd17",n=(0,i.cC)(t.docId??void 0);return(0,d.jsx)(m,{href:t.href,icon:s,title:t.label,description:t.description??n?.description})}function x(e){let{item:t}=e;switch(t.type){case"link":return(0,d.jsx)(b,{item:t});case"category":return(0,d.jsx)(h,{item:t});default:throw new Error(`unknown item type ${JSON.stringify(t)}`)}}function v(e){let{className:t}=e;const s=(0,i.$S)();return(0,d.jsx)(p,{items:s.items,className:t})}function p(e){const{items:t,className:s}=e;if(!t)return(0,d.jsx)(v,{...e});const a=(0,i.d1)(t);return(0,d.jsx)("section",{className:(0,n.A)("row",s),children:a.map(((e,t)=>(0,d.jsx)("article",{className:"col col--6 margin-bottom--lg",children:(0,d.jsx)(x,{item:e})},t)))})}},5847:(e,t,s)=>{s.r(t),s.d(t,{default:()=>v});s(6540);var n=s(1003),i=s(4142),a=s(6025),r=s(3514),l=s(6929),c=s(1878),o=s(4267),d=s(1243),u=s(1107);const m={generatedIndexPage:"generatedIndexPage_vN6x",list:"list_eTzJ",title:"title_kItE"};var h=s(4848);function b(e){let{categoryGeneratedIndex:t}=e;return(0,h.jsx)(n.be,{title:t.title,description:t.description,keywords:t.keywords,image:(0,a.A)(t.image)})}function x(e){let{categoryGeneratedIndex:t}=e;const s=(0,i.$S)();return(0,h.jsxs)("div",{className:m.generatedIndexPage,children:[(0,h.jsx)(c.A,{}),(0,h.jsx)(d.A,{}),(0,h.jsx)(o.A,{}),(0,h.jsxs)("header",{children:[(0,h.jsx)(u.A,{as:"h1",className:m.title,children:t.title}),t.description&&(0,h.jsx)("p",{children:t.description})]}),(0,h.jsx)("article",{className:"margin-top--lg",children:(0,h.jsx)(r.A,{items:s.items,className:m.list})}),(0,h.jsx)("footer",{className:"margin-top--lg",children:(0,h.jsx)(l.A,{previous:t.navigation.previous,next:t.navigation.next})})]})}function v(e){return(0,h.jsxs)(h.Fragment,{children:[(0,h.jsx)(b,{...e}),(0,h.jsx)(x,{...e})]})}},6929:(e,t,s)=>{s.d(t,{A:()=>c});s(6540);var n=s(1312),i=s(8215),a=s(8774),r=s(4848);function l(e){const{permalink:t,title:s,subLabel:n,isNext:l}=e;return(0,r.jsxs)(a.A,{className:(0,i.A)("pagination-nav__link",l?"pagination-nav__link--next":"pagination-nav__link--prev"),to:t,children:[n&&(0,r.jsx)("div",{className:"pagination-nav__sublabel",children:n}),(0,r.jsx)("div",{className:"pagination-nav__label",children:s})]})}function c(e){const{previous:t,next:s}=e;return(0,r.jsxs)("nav",{className:"pagination-nav docusaurus-mt-lg","aria-label":(0,n.translate)({id:"theme.docs.paginator.navAriaLabel",message:"Docs pages",description:"The ARIA label for the docs pagination"}),children:[t&&(0,r.jsx)(l,{...t,subLabel:(0,r.jsx)(n.default,{id:"theme.docs.paginator.previous",description:"The label used to navigate to the previous doc",children:"Previous"})}),s&&(0,r.jsx)(l,{...s,subLabel:(0,r.jsx)(n.default,{id:"theme.docs.paginator.next",description:"The label used to navigate to the next doc",children:"Next"}),isNext:!0})]})}},4267:(e,t,s)=>{s.d(t,{A:()=>c});s(6540);var n=s(8215),i=s(1312),a=s(7559),r=s(2252),l=s(4848);function c(e){let{className:t}=e;const s=(0,r.r)();return s.badge?(0,l.jsx)("span",{className:(0,n.A)(t,a.G.docs.docVersionBadge,"badge badge--secondary"),children:(0,l.jsx)(i.default,{id:"theme.docs.versionBadge.label",values:{versionLabel:s.label},children:"Version: {versionLabel}"})}):null}},1878:(e,t,s)=>{s.d(t,{A:()=>v});s(6540);var n=s(8215),i=s(4586),a=s(8774),r=s(1312),l=s(4070),c=s(7559),o=s(5597),d=s(2252),u=s(4848);const m={unreleased:function(e){let{siteTitle:t,versionMetadata:s}=e;return(0,u.jsx)(r.default,{id:"theme.docs.versions.unreleasedVersionLabel",description:"The label used to tell the user that he's browsing an unreleased doc version",values:{siteTitle:t,versionLabel:(0,u.jsx)("b",{children:s.label})},children:"This is unreleased documentation for {siteTitle} {versionLabel} version."})},unmaintained:function(e){let{siteTitle:t,versionMetadata:s}=e;return(0,u.jsx)(r.default,{id:"theme.docs.versions.unmaintainedVersionLabel",description:"The label used to tell the user that he's browsing an unmaintained doc version",values:{siteTitle:t,versionLabel:(0,u.jsx)("b",{children:s.label})},children:"This is documentation for {siteTitle} {versionLabel}, which is no longer actively maintained."})}};function h(e){const t=m[e.versionMetadata.banner];return(0,u.jsx)(t,{...e})}function b(e){let{versionLabel:t,to:s,onClick:n}=e;return(0,u.jsx)(r.default,{id:"theme.docs.versions.latestVersionSuggestionLabel",description:"The label used to tell the user to check the latest version",values:{versionLabel:t,latestVersionLink:(0,u.jsx)("b",{children:(0,u.jsx)(a.A,{to:s,onClick:n,children:(0,u.jsx)(r.default,{id:"theme.docs.versions.latestVersionLinkLabel",description:"The label used for the latest version suggestion link label",children:"latest version"})})})},children:"For up-to-date documentation, see the {latestVersionLink} ({versionLabel})."})}function x(e){let{className:t,versionMetadata:s}=e;const{siteConfig:{title:a}}=(0,i.A)(),{pluginId:r}=(0,l.vT)({failfast:!0}),{savePreferredVersionName:d}=(0,o.g1)(r),{latestDocSuggestion:m,latestVersionSuggestion:x}=(0,l.HW)(r),v=m??(p=x).docs.find((e=>e.id===p.mainDocId));var p;return(0,u.jsxs)("div",{className:(0,n.A)(t,c.G.docs.docVersionBanner,"alert alert--warning margin-bottom--md"),role:"alert",children:[(0,u.jsx)("div",{children:(0,u.jsx)(h,{siteTitle:a,versionMetadata:s})}),(0,u.jsx)("div",{className:"margin-top--md",children:(0,u.jsx)(b,{versionLabel:x.label,to:v.path,onClick:()=>d(x.name)})})]})}function v(e){let{className:t}=e;const s=(0,d.r)();return s.banner?(0,u.jsx)(x,{className:t,versionMetadata:s}):null}}}]);