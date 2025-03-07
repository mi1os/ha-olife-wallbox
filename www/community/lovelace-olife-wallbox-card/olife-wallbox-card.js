/**
 * Olife Wallbox Card
 * Custom Lovelace card for Olife Energy Wallbox integration
 * 
 * @author mi1os
 * @version 1.0.0
 */

class OlifeWallboxCard extends HTMLElement {
  // Define properties and default configuration
  static getStubConfig() {
    return {
      title: "Olife Wallbox",
      entity: "",
      power_entity: "",
      energy_entity: "",
      current_limit_entity: "",
      show_stats: true,
      show_controls: true
    };
  }

  // Set internal properties
  constructor() {
    super();
    this._config = {};
    this.state = {};
    this.entityIds = new Set();
  }

  // Handle updated configuration
  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }

    this._config = {
      title: config.title || "Olife Wallbox",
      entity: config.entity,
      power_entity: config.power_entity || "",
      energy_entity: config.energy_entity || "",
      current_limit_entity: config.current_limit_entity || "",
      show_stats: config.show_stats !== false,
      show_controls: config.show_controls !== false,
      theme: config.theme || "default"
    };

    // Keep track of entities to monitor
    this.entityIds = new Set([
      this._config.entity,
      this._config.power_entity,
      this._config.energy_entity,
      this._config.current_limit_entity
    ].filter(id => id));
  }

  // Define card properties
  getCardSize() {
    return this._config.show_controls ? 4 : 2;
  }

  // Handle Home Assistant connection
  set hass(hass) {
    this._hass = hass;
    let updated = false;

    // Update all entity states we're monitoring
    this.entityIds.forEach(id => {
      const entityState = hass.states[id];
      if (entityState && this.state[id] !== JSON.stringify(entityState)) {
        this.state[id] = JSON.stringify(entityState);
        updated = true;
      }
    });

    // Only update the UI if something has changed
    if (updated) {
      this._updateUI();
    }

    if (!this.content) {
      this._createCard();
      this._updateUI();
    }
  }

  // Create the card HTML structure
  _createCard() {
    // Card container
    this.content = document.createElement("ha-card");
    this.content.className = "olife-wallbox-card";
    this.appendChild(this.content);

    // Card header
    const header = document.createElement("div");
    header.className = "card-header";
    header.innerHTML = `
      <div class="name">${this._config.title}</div>
    `;
    this.content.appendChild(header);

    // Card content
    const content = document.createElement("div");
    content.className = "card-content";
    
    // Status section
    const statusSection = document.createElement("div");
    statusSection.className = "status-section";
    statusSection.innerHTML = `
      <div class="status-wrapper">
        <div class="status-icon">
          <ha-icon icon="mdi:ev-station"></ha-icon>
        </div>
        <div class="status-info">
          <div class="status-text"></div>
          <div class="secondary-info"></div>
        </div>
      </div>
    `;
    content.appendChild(statusSection);
    
    // Stats section (conditional)
    if (this._config.show_stats) {
      const statsSection = document.createElement("div");
      statsSection.className = "stats-section";
      statsSection.innerHTML = `
        <div class="stat-item power">
          <ha-icon icon="mdi:flash"></ha-icon>
          <span class="stat-value power-value">--</span>
          <span class="stat-label">Power</span>
        </div>
        <div class="stat-item energy">
          <ha-icon icon="mdi:counter"></ha-icon>
          <span class="stat-value energy-value">--</span>
          <span class="stat-label">Energy</span>
        </div>
        <div class="stat-item limit">
          <ha-icon icon="mdi:speedometer"></ha-icon>
          <span class="stat-value limit-value">--</span>
          <span class="stat-label">Current Limit</span>
        </div>
      `;
      content.appendChild(statsSection);
    }
    
    this.content.appendChild(content);
    
    // Controls section (conditional)
    if (this._config.show_controls) {
      const controlsSection = document.createElement("div");
      controlsSection.className = "controls-section";
      
      // Toggle charging button
      const toggleBtn = document.createElement("mwc-button");
      toggleBtn.className = "toggle-button";
      toggleBtn.raised = true;
      toggleBtn.addEventListener("click", () => this._toggleCharging());
      controlsSection.appendChild(toggleBtn);
      
      // Adjust current limit slider (if entity specified)
      if (this._config.current_limit_entity) {
        const sliderContainer = document.createElement("div");
        sliderContainer.className = "slider-container";
        sliderContainer.innerHTML = `
          <div class="slider-label">Current Limit</div>
          <div class="slider-row">
            <ha-slider
              min="6"
              max="32"
              step="1"
              pin
              class="current-slider"
            ></ha-slider>
            <div class="slider-value"></div>
          </div>
        `;
        controlsSection.appendChild(sliderContainer);
        
        // Set up slider events
        const slider = sliderContainer.querySelector("ha-slider");
        slider.addEventListener("change", (e) => {
          this._setCurrentLimit(parseInt(e.target.value));
        });
      }
      
      this.content.appendChild(controlsSection);
    }
    
    // Add styles
    this._addStyles();
  }

  // Update UI based on entity states
  _updateUI() {
    if (!this._hass || !this.content) return;
    
    const mainEntity = this._hass.states[this._config.entity];
    if (!mainEntity) return;
    
    // Update status section
    const statusText = this.content.querySelector(".status-text");
    const secondaryInfo = this.content.querySelector(".secondary-info");
    const statusIcon = this.content.querySelector(".status-icon ha-icon");
    
    statusText.textContent = this._getMainStatus(mainEntity);
    secondaryInfo.textContent = this._getSecondaryStatus(mainEntity);
    
    // Update icon based on state
    const icon = this._getStatusIcon(mainEntity.state);
    if (statusIcon) {
      statusIcon.setAttribute("icon", icon);
    }
    
    // Update stats section if present
    if (this._config.show_stats) {
      // Update power
      if (this._config.power_entity) {
        const powerEntity = this._hass.states[this._config.power_entity];
        const powerValue = this.content.querySelector(".power-value");
        if (powerEntity && powerValue) {
          powerValue.textContent = `${parseFloat(powerEntity.state).toFixed(1)} ${powerEntity.attributes.unit_of_measurement || "W"}`;
        }
      }
      
      // Update energy
      if (this._config.energy_entity) {
        const energyEntity = this._hass.states[this._config.energy_entity];
        const energyValue = this.content.querySelector(".energy-value");
        if (energyEntity && energyValue) {
          energyValue.textContent = `${parseFloat(energyEntity.state).toFixed(2)} ${energyEntity.attributes.unit_of_measurement || "kWh"}`;
        }
      }
      
      // Update current limit
      if (this._config.current_limit_entity) {
        const limitEntity = this._hass.states[this._config.current_limit_entity];
        const limitValue = this.content.querySelector(".limit-value");
        if (limitEntity && limitValue) {
          limitValue.textContent = `${parseFloat(limitEntity.state).toFixed(0)} ${limitEntity.attributes.unit_of_measurement || "A"}`;
        }
      }
    }
    
    // Update controls if present
    if (this._config.show_controls) {
      // Update toggle button
      const toggleBtn = this.content.querySelector(".toggle-button");
      if (toggleBtn) {
        const isCharging = mainEntity.state === "on" || mainEntity.state === "charging";
        toggleBtn.textContent = isCharging ? "Stop Charging" : "Start Charging";
        toggleBtn.style.backgroundColor = isCharging ? "var(--error-color, #f44336)" : "var(--success-color, #4CAF50)";
      }
      
      // Update slider if present
      if (this._config.current_limit_entity) {
        const limitEntity = this._hass.states[this._config.current_limit_entity];
        const slider = this.content.querySelector("ha-slider");
        const sliderValue = this.content.querySelector(".slider-value");
        
        if (limitEntity && slider && sliderValue) {
          const value = parseFloat(limitEntity.state);
          slider.value = value;
          sliderValue.textContent = `${value} ${limitEntity.attributes.unit_of_measurement || "A"}`;
          
          // Update min/max if available in attributes
          if (limitEntity.attributes.min && limitEntity.attributes.max) {
            slider.min = limitEntity.attributes.min;
            slider.max = limitEntity.attributes.max;
          }
        }
      }
    }
  }
  
  // Helper methods for UI
  _getMainStatus(entity) {
    // For a switch entity
    if (entity.attributes.device_class === "switch") {
      return entity.state === "on" ? "Charging" : "Stopped";
    }
    
    // For the EV State sensor
    if (entity.attributes.friendly_name && entity.attributes.friendly_name.includes("EV State")) {
      return entity.state;
    }
    
    return entity.state.charAt(0).toUpperCase() + entity.state.slice(1);
  }
  
  _getSecondaryStatus(entity) {
    // Try to get additional status info
    const lastUpdated = new Date(entity.last_updated);
    
    // Format last updated time
    const timeString = lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    // Return a formatted secondary status
    if (entity.attributes.device_class === "switch") {
      return `Last updated: ${timeString}`;
    }
    
    // Try to include additional details from attributes
    if (entity.attributes.description) {
      return entity.attributes.description;
    }
    
    return `Last updated: ${timeString}`;
  }
  
  _getStatusIcon(state) {
    // Return appropriate icon based on state
    switch (state) {
      case "on":
      case "charging":
        return "mdi:battery-charging";
      case "ready":
      case "waiting":
        return "mdi:ev-station";
      case "off":
      case "not_charging":
        return "mdi:power-plug-off";
      case "error":
        return "mdi:alert-circle";
      default:
        return "mdi:ev-station";
    }
  }
  
  // Control methods
  _toggleCharging() {
    const mainEntity = this._hass.states[this._config.entity];
    if (!mainEntity) return;
    
    const isCharging = mainEntity.state === "on" || mainEntity.state === "charging";
    const service = isCharging ? "turn_off" : "turn_on";
    
    // Call the appropriate service
    this._hass.callService("switch", service, {
      entity_id: this._config.entity
    });
  }
  
  _setCurrentLimit(value) {
    if (!this._config.current_limit_entity) return;
    
    // Call the set_value service for the number entity
    this._hass.callService("number", "set_value", {
      entity_id: this._config.current_limit_entity,
      value: value
    });
  }
  
  // Add card styles
  _addStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .olife-wallbox-card {
        padding-bottom: 16px;
      }
      .card-content {
        padding: 16px;
      }
      .status-section {
        margin-bottom: 20px;
      }
      .status-wrapper {
        display: flex;
        align-items: center;
      }
      .status-icon {
        margin-right: 16px;
      }
      .status-icon ha-icon {
        width: 40px;
        height: 40px;
        --mdc-icon-size: 40px;
        color: var(--primary-color);
      }
      .status-info {
        flex: 1;
      }
      .status-text {
        font-size: 24px;
        font-weight: 500;
        line-height: 1.2;
      }
      .secondary-info {
        color: var(--secondary-text-color);
        font-size: 14px;
      }
      .stats-section {
        display: flex;
        justify-content: space-between;
        margin: 16px 0;
        padding: 16px 0;
        border-top: 1px solid var(--divider-color);
        border-bottom: 1px solid var(--divider-color);
      }
      .stat-item {
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
      }
      .stat-item ha-icon {
        color: var(--secondary-text-color);
        margin-bottom: 4px;
      }
      .stat-value {
        font-size: 18px;
        font-weight: 500;
      }
      .stat-label {
        font-size: 12px;
        color: var(--secondary-text-color);
      }
      .controls-section {
        padding-top: 8px;
      }
      .toggle-button {
        width: 100%;
        margin-bottom: 16px;
        --mdc-theme-primary: var(--primary-color);
      }
      .slider-container {
        margin-top: 16px;
      }
      .slider-label {
        font-size: 14px;
        margin-bottom: 8px;
        color: var(--primary-text-color);
      }
      .slider-row {
        display: flex;
        align-items: center;
      }
      .slider-row ha-slider {
        flex: 1;
      }
      .slider-value {
        min-width: 40px;
        text-align: right;
        margin-left: 8px;
      }
    `;
    this.content.appendChild(style);
  }
}

// Register the card
customElements.define("olife-wallbox-card", OlifeWallboxCard);

// Add card to HACS frontend
window.customCards = window.customCards || [];
window.customCards.push({
  type: "olife-wallbox-card",
  name: "Olife Wallbox Card",
  description: "A card for monitoring and controlling your Olife Energy Wallbox"
}); 