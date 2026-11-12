package EcoGrid.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import org.hibernate.annotations.OnDelete;
import org.hibernate.annotations.OnDeleteAction;

import java.math.BigDecimal;

@Entity
@Table(name = "OFERTADEMANDAOMIE")
public class Ofertademandaomie {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "IDCURVA", nullable = false)
    private Long id;

    @NotNull
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @OnDelete(action = OnDeleteAction.RESTRICT)
    @JoinColumn(name = "IDTIEMPO", nullable = false)
    private Tiempohorario idtiempo;

    @Size(max = 10)
    @NotNull
    @Column(name = "PAIS", nullable = false, length = 10)
    private String pais;

    @Column(name = "POTENCIACOMPRAVENTA", precision = 12, scale = 4)
    private BigDecimal potenciacompraventa;

    @Column(name = "PRECIOCOMPRAVENTA", precision = 12, scale = 4)
    private BigDecimal preciocompraventa;

    @Size(max = 50)
    @Column(name = "TIPOFERTA", length = 50)
    private String tipoferta;

    @Size(max = 50)
    @Column(name = "TIPOLOGIAOFERTA", length = 50)
    private String tipologiaoferta;

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

    public String getPais() {
        return pais;
    }

    public void setPais(String pais) {
        this.pais = pais;
    }

    public BigDecimal getPotenciacompraventa() {
        return potenciacompraventa;
    }

    public void setPotenciacompraventa(BigDecimal potenciacompraventa) {
        this.potenciacompraventa = potenciacompraventa;
    }

    public BigDecimal getPreciocompraventa() {
        return preciocompraventa;
    }

    public void setPreciocompraventa(BigDecimal preciocompraventa) {
        this.preciocompraventa = preciocompraventa;
    }

    public String getTipoferta() {
        return tipoferta;
    }

    public void setTipoferta(String tipoferta) {
        this.tipoferta = tipoferta;
    }

    public String getTipologiaoferta() {
        return tipologiaoferta;
    }

    public void setTipologiaoferta(String tipologiaoferta) {
        this.tipologiaoferta = tipologiaoferta;
    }

}