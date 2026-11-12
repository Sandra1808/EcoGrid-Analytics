package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "METEOROLOGIA")
public class Meteorologia {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDMETEO", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDCCAA", nullable = false)
    private Comunidadautonoma idccaa;

    @Column(name = "TEMPERATURA_2M", precision = 5, scale = 2)
    private BigDecimal temperatura2m;

    @Column(name = "TEMPERATURAAPARENTE", precision = 5, scale = 2)
    private BigDecimal temperaturaaparente;

    @Column(name = "VIENTO_10M", precision = 5, scale = 2)
    private BigDecimal viento10m;

    @Column(name = "VIENTO_80M", precision = 5, scale = 2)
    private BigDecimal viento80m;

    @Column(name = "VIENTO_120M", precision = 5, scale = 2)
    private BigDecimal viento120m;

    @Column(name = "VIENTO_180M", precision = 5, scale = 2)
    private BigDecimal viento180m;

    @Column(name = "VIENTO_DIR_10M", precision = 5, scale = 2)
    private BigDecimal vientoDir10m;

    @Column(name = "VIENTO_DIR_80M", precision = 5, scale = 2)
    private BigDecimal vientoDir80m;

    @Column(name = "VIENTO_DIR_120M", precision = 5, scale = 2)
    private BigDecimal vientoDir120m;

    @Column(name = "VIENTO_DIR_180M", precision = 5, scale = 2)
    private BigDecimal vientoDir180m;

    @Column(name = "RADIACION_DIRECTA", precision = 8, scale = 2)
    private BigDecimal radiacionDirecta;

    @Column(name = "SHORTWAVE_RADIATION", precision = 8, scale = 2)
    private BigDecimal shortwaveRadiation;

    @Column(name = "GLOBAL_TILTED_IRRADIANCE", precision = 8, scale = 2)
    private BigDecimal globalTiltedIrradiance;

    @Column(name = "COBERTURA_NUBES")
    private Short coberturaNubes;

    @Column(name = "HUMEDAD_RELATIVA")
    private Short humedadRelativa;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Tiempohorario getIdtiempo() {
        return idtiempo;
    }

    public void setIdtiempo(Tiempohorario idtiempo) {
        this.idtiempo = idtiempo;
    }

    public Comunidadautonoma getIdccaa() {
        return idccaa;
    }

    public void setIdccaa(Comunidadautonoma idccaa) {
        this.idccaa = idccaa;
    }

    public BigDecimal getTemperatura2m() {
        return temperatura2m;
    }

    public void setTemperatura2m(BigDecimal temperatura2m) {
        this.temperatura2m = temperatura2m;
    }

    public BigDecimal getTemperaturaaparente() {
        return temperaturaaparente;
    }

    public void setTemperaturaaparente(BigDecimal temperaturaaparente) {
        this.temperaturaaparente = temperaturaaparente;
    }

    public BigDecimal getViento10m() {
        return viento10m;
    }

    public void setViento10m(BigDecimal viento10m) {
        this.viento10m = viento10m;
    }

    public BigDecimal getViento80m() {
        return viento80m;
    }

    public void setViento80m(BigDecimal viento80m) {
        this.viento80m = viento80m;
    }

    public BigDecimal getViento120m() {
        return viento120m;
    }

    public void setViento120m(BigDecimal viento120m) {
        this.viento120m = viento120m;
    }

    public BigDecimal getViento180m() {
        return viento180m;
    }

    public void setViento180m(BigDecimal viento180m) {
        this.viento180m = viento180m;
    }

    public BigDecimal getVientoDir10m() {
        return vientoDir10m;
    }

    public void setVientoDir10m(BigDecimal vientoDir10m) {
        this.vientoDir10m = vientoDir10m;
    }

    public BigDecimal getVientoDir80m() {
        return vientoDir80m;
    }

    public void setVientoDir80m(BigDecimal vientoDir80m) {
        this.vientoDir80m = vientoDir80m;
    }

    public BigDecimal getVientoDir120m() {
        return vientoDir120m;
    }

    public void setVientoDir120m(BigDecimal vientoDir120m) {
        this.vientoDir120m = vientoDir120m;
    }

    public BigDecimal getVientoDir180m() {
        return vientoDir180m;
    }

    public void setVientoDir180m(BigDecimal vientoDir180m) {
        this.vientoDir180m = vientoDir180m;
    }

    public BigDecimal getRadiacionDirecta() {
        return radiacionDirecta;
    }

    public void setRadiacionDirecta(BigDecimal radiacionDirecta) {
        this.radiacionDirecta = radiacionDirecta;
    }

    public BigDecimal getShortwaveRadiation() {
        return shortwaveRadiation;
    }

    public void setShortwaveRadiation(BigDecimal shortwaveRadiation) {
        this.shortwaveRadiation = shortwaveRadiation;
    }

    public BigDecimal getGlobalTiltedIrradiance() {
        return globalTiltedIrradiance;
    }

    public void setGlobalTiltedIrradiance(BigDecimal globalTiltedIrradiance) {
        this.globalTiltedIrradiance = globalTiltedIrradiance;
    }

    public Short getCoberturaNubes() {
        return coberturaNubes;
    }

    public void setCoberturaNubes(Short coberturaNubes) {
        this.coberturaNubes = coberturaNubes;
    }

    public Short getHumedadRelativa() {
        return humedadRelativa;
    }

    public void setHumedadRelativa(Short humedadRelativa) {
        this.humedadRelativa = humedadRelativa;
    }

}