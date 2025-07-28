import React from "react";

export default function PageHeader({ title, subtitle, children }) {
  return (
    <div className="w-full mb-8 flex flex-col gap-1">
      <h1 className="text-3xl font-bold">{title}</h1>
      {subtitle && <p className="text-gray-600">{subtitle}</p>}
      {children}
    </div>
  );
}
